#!/usr/bin/env python3

from Cinema.Prompt import Launcher, Visualiser
import numpy as np
import argparse
from Cinema.Interface.Utils import findData
import os

HAS_SPARK = False

try:
    import pyspark
    HAS_SPARK = True
except ImportError as ex:
    print(ex)
    print('No spark found. Will run in a single thread.')


def get_available_cpus():
    return len(os.sched_getaffinity(0))


def get_spark_app_name(gdml_fp, neutron_count):
    _t = gdml_fp.rsplit('/')[-1]
    return f"Prompt_{_t}_{neutron_count}"


def get_spark_master(spark_master_str):
    if len(spark_master_str) == 0:
        cpus = get_available_cpus()
        return 'local' if cpus == 0 else f'local[{cpus}]'
    else:
        return spark_master_str


def run(item):
    """
    Run prompt.

    :param item: [neutrons_num, random_seed]
    :type item: np.ndarray
    :return:
    """
    myLcher = Launcher()
    myLcher.setSeed(item[1])
    _t = SparkFiles.get(inputfile.rsplit('/')[-1])
    myLcher.loadGeometry(_t)
    myLcher.go(item[0], recordTrj=False)


def create_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--gdml', action='store', type=str, default='',
                        dest='gdml', help='input gdml file')
    parser.add_argument('-v', '--visualize', action='store_true', dest='visualize', help='flag to visualize gdml model')
    parser.add_argument('-s', '--seed', action='store', type=int, default=4096,
                        dest='seed', help='random seed number')
    parser.add_argument('-n', '--neutronNum', action='store', type=float, default=100,
                        dest='neutronNum', help='neutron number')
    parser.add_argument('-b', '--blacklist', type=str, nargs='+', dest='blacklist',
                        help='solid mesh blacklist to inform the geometry mesh loader ')
    parser.add_argument('-d', '--dumpmesh', action='store_true', dest='dumpmesh', help='dump mesh into disk')
    parser.add_argument('-m', '--nSegments', action='store', type=int, default=30,
                        dest='nSegments', help='number of verts a volume')
    parser.add_argument('-p', '--spark-master', action='store', type=str, default='',
                        dest='spark_master', help='the address of spark master')
    parser.add_argument('-k', '--data-partitions', action='store', type=int, default=2,
                        dest='data_partitions',
                        help='the partitions of spark data. It should be less than the available cpu cores')

    # TODO:
    # parser.add_argument('-l', '--geoLayer', action='store', type=float, default=0,
    #                     dest='geoLayer', help='geometry tree layers to be shown')
    #
    # parser.add_argument('-n', '--neutronNum', action='store', type=float, default=100,
    #                     dest='num', help='maxium number of verts to represent a volume')
    #
    # parser.add_argument('-n', '--neutronNum', action='store', type=float, default=100,
    #                     dest='neutronNum', help='enforce all defined physical volume to be placed into the world')

    # parser.add_argument('-n', '--neutronNum', action='store', type=float, default=100,
    #                     dest='neutronNum', help='print trajectores in the terminal')
    return parser


parser = create_argparser()
args = parser.parse_args()
inputfile = args.gdml
printTraj = False
neutronNum = int(args.neutronNum)

if not os.path.isfile(inputfile):
    inputfile = findData(f'gdml/{inputfile}', '.')
    if not os.path.isfile(inputfile):
        raise IOError(f'The input GDML file {args.gdml} is not found.')

if HAS_SPARK:  # run in spark
    from pyspark.sql import SparkSession
    from pyspark import SparkFiles

    app_name = get_spark_app_name(inputfile, neutronNum)
    master = get_spark_master(args.spark_master)
    data_partitions = args.data_partitions
    spark = SparkSession.builder.appName(app_name).master(master).getOrCreate()
    sc = spark.sparkContext
    sc.addFile(inputfile)
    app_id = sc.applicationId
    cores = int(sc.getConf().get('spark.cores.max', f'{data_partitions}'))

    a = neutronNum // cores
    b = a + 1
    count_a = cores * b - neutronNum
    count_b = cores - count_a
    neutrons = np.ones((count_a, ), dtype=np.int32) * a
    if count_b > 0:
        t = np.ones((count_b, ), dtype=np.int32) * b
        neutrons = np.concatenate((neutrons, t), axis=0)
    seeds = np.arange(1, cores + 1, dtype=np.int32)
    d = np.stack((neutrons, seeds), axis=1)
    np.savetxt('input_dump.txt', d, fmt='%i', delimiter=',', header='neutrons,seed')

    sc.parallelize(d, cores).map(lambda item: run(item)).collect()
    # jsc = spark._jsc.sc()
    # st = jsc.statusTracker()
    # r1 = jsc.getExecutorMemoryStatus().keys() # will print all the executors + driver available
    # r2 = len([executor.host() for executor in st.getExecutorInfos()]) - 1
    print(f'Spark app id: {app_id}.')
    spark.stop()
    print('Done.')

else:  # run in a single thread
    import time
    start = time.time()

    rdseed = args.seed
    myLcher = Launcher()
    myLcher.setSeed(rdseed)
    myLcher.loadGeometry(inputfile)

    if args.visualize is True:
        import matplotlib.pyplot as plt
        v = Visualiser(args.blacklist, printWorld=False, nSegments=args.nSegments, doDumpMesh=args.dumpmesh)
        for i in range(int(args.neutronNum)):
            myLcher.go(1, recordTrj=True, timer=False)
            trj = myLcher.getTrajectory()
            try:
                v.addTrj(trj)
            except ValueError:
                print("skip ValueError in File '/Prompt/scripts/prompt.py', in <module>, v.addLine(trj)")
        v.show()
    else:
        myLcher.go(int(args.neutronNum), recordTrj=False)

    t = time.time() - start
    print(f"Done in {t} s.")


