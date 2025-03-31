import os
import subprocess
import numpy as np
import logging
from multiprocessing import Pool
import argparse

class FileProcessor:
    def __init__(self, calc, dirname, output_dir, log_file='process.log', num_processes=40, temperatures=None, ext='endf'):
        self.calc = calc
        self.dirname = dirname + '/'
        self.output_dir = output_dir + '/'
        self.num_processes = num_processes
        self.ext = ext
        self.fn = []
        self.const_boltzmann = 8.6173303e-11
        self.temp = np.array(temperatures) if temperatures else []
        self.setup_logging(log_file)
        self.collect_files()

    def setup_logging(self, log_file):
        logging.basicConfig(filename=log_file, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger()

    def collect_files(self):
        for files in os.listdir(self.dirname):
            if files.endswith(self.ext):
                self.fn.append(files)
        self.fn.sort()
        print(self.fn)
        self.logger.info(f'Collected {len(self.fn)} files with extension {self.ext}')

    def run_file(self, f):
        try:
            if os.path.exists("TEM"):
                self.logger.info("File TEM found. Exiting loop.")
                return

            if self.calc == 'endf':
                result1 = subprocess.run(
                    f'endf2gnds.py --skipCovariances --skipBadData --ignoreBadDate --continuumSpectraFix {self.dirname+f} {self.output_dir+f+".xml"}',
                    shell=True, check=True, stderr=subprocess.PIPE, text=True)

            elif self.calc == 'mc':
                substr = " "
                for t in self.temp:
                    substr += ' -t ' + str(t * self.const_boltzmann) + '  '

                # Run the second subprocess
                result1 = subprocess.run(
                    f'processProtare.py {substr} -mc --hybrid {self.dirname+f} {self.output_dir+f}',
                    shell=True, check=True, stderr=subprocess.PIPE, text=True)

            elif self.calc == 'urr':
                file_name_without_extension, file_extension = os.path.splitext(f)
                new_file_name = file_name_without_extension + ".urr" + file_extension
                result1 = subprocess.run(
                    f'processURR.py {self.output_dir+f} 10 --hybrid -o {self.output_dir+new_file_name}',
                    shell=True, check=True, stderr=subprocess.PIPE, text=True)

            self.logger.info(f'{f} is done @ {self.temp} Kelvin')
            print(f'\033[92m{f} is done @ {self.temp} kelvin\033[0m')

        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()
            self.logger.error(f'{f} failed: {e} \n {error_message}')
            print(f'\033[91m{f} failed: {error_message}\033[0m')

    def process_files(self):
        with Pool(self.num_processes) as p:
            p.map(self.run_file, self.fn)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process files in a directory with multiprocessing.')
    parser.add_argument('calc', action='store', type=str, default='', 
                          help='calculation type: endf, mc, urr.(default: %(default)s)')
    parser.add_argument('-d', '--dirname', type=str, required=True, help='Directory containing input files. (default: %(default)s)')
    parser.add_argument('-o', '--output_dir', type=str, required=True, help='Directory for storing output files. (default: %(default)s)')
    parser.add_argument('-l', '--log_file', type=str, default='process.log', help='Log file name. (default: %(default)s)')
    parser.add_argument('-n', '--num_processes', type=int, default=40, help='Number of processes in the pool. (default: %(default)s)')
    parser.add_argument('-t', '--temperatures', type=float, nargs='+', default=[], help='List of temperatures in Kelvin. (default: %(default)s)')
    parser.add_argument('-e', '--ext', type=str, required=True, help='File extension to filter by. (default: %(default)s)')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    if args.calc not in ['endf', 'mc', 'urr']:
        raise ValueError("Invalid calculation type. Use 'endf', 'mc', or 'urr'.")
    
    processor = FileProcessor(
        calc=args.calc,
        dirname=args.dirname,
        output_dir=args.output_dir,
        log_file=args.log_file,
        num_processes=args.num_processes,
        temperatures=args.temperatures,
        ext=args.ext
    )
    processor.process_files()



