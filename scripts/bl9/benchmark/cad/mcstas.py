#!/usr/bin/env python3
import sys
import os
import json
# Root of the bl9 script tree (two levels up from this file), holding the
# local modules (jsonReader) and geo_data/.
projectpath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + '/'
sys.path.append(projectpath)
from jsonReader import JsonParser

GEO_FILE = os.path.join(projectpath, 'geo_data/section.json')

guideinfo = JsonParser(GEO_FILE)
zmin,zmax,zmid = guideinfo.bound_zinfo()
xmin,xmax,_ = guideinfo.bound_xinfo()
ymin,ymax,_ = guideinfo.bound_yinfo()

eell = guideinfo.readIn()
output_file = 'guide_channels.instr'  

# 定义需要创建的 guide_channel 数量  
num_channels = len(eell)
eell = list(eell)
# 打开输出文件  
with open(output_file, 'w') as f:  
    # 写入文件头  
    f.write("DEFINE INSTRUMENT bl9_guide()\n\n")  
    f.write("TRACE\n\n")  
    # f.write("COMPONENT origin = Progress_bar() AT (0,0,origin_location) ABSOLUTE\n\n")

    # # write source
    # f.write(f"COMPONENT Source = Source_gen(\n")
    # f.write(f"dist = 5, \n")
    # f.write(f"focus_xw = 0.06, \n")
    # f.write(f"focus_yh = 0.06, \n")
    # f.write(f"lambda0 = 3, \n")
    # f.write(f"dlambda = 2.9,\n")
    # f.write(f"yheight = 0.02, \n")
    # f.write(f"xwidth = 0.02,\n")
    # f.write(f"T1=293) \n")
    # f.write(f"AT (0, 0, 8.2165-5) RELATIVE PREVIOUS\n\n")

    # energy Monitor
    f.write(f"COMPONENT eng_entry_Monitor = Monitor_nD(\n")
    f.write(f'options = "log energy, limits=[-1 5], bins=100",\n')
    f.write(f"xwidth = 0.04,\n")
    f.write(f"yheight = 0.08\n")
    f.write(")\n")  
    f.write(f"AT (0, 0, {zmin * 0.001 - 0.7}) RELATIVE  origin\n\n")

    # psd x Monitor at entry
    f.write(f"COMPONENT x_mon_entry = Monitor_nD(\n")
    f.write(f'options = "x bins=101",\n')
    f.write(f"xwidth = 0.04,\n")
    f.write(f"yheight = 0.08\n")
    f.write(")\n")  
    f.write(f"AT (0, 0, {zmin * 0.001 - 0.7}) RELATIVE  origin\n\n")

    # psd y Monitor at exit
    f.write(f"COMPONENT y_mon_entry = Monitor_nD(\n")
    f.write(f'options = "y bins=100",\n')
    f.write(f"xwidth = 0.04,\n")
    f.write(f"yheight = 0.08\n")
    f.write(")\n")  
    f.write(f"AT (0, 0, {zmin * 0.001 - 0.7}) RELATIVE  origin\n\n")

    # 循环生成 guide_channel  
    for i in range(num_channels):  
        w1 = eell[i]['entryOpening']['halfwidth'] * 2 * 0.001
        h1 = eell[i]['entryOpening']['halfheight'] * 2 * 0.001
        w2 = eell[i]['exitOpening']['halfwidth'] * 2 * 0.001
        h2 = eell[i]['exitOpening']['halfheight'] * 2 * 0.001
        ll = eell[i]['length'] * 0.001
        location = eell[i]['zlocation'] * 0.001

        # # Guide_channeled 定义 guide_channel 的位置和参数  
        # f.write(f"COMPONENT Guide_section{i+1} = Guide_channeled(\n")  
        # f.write(f"w1={w1},\n")  
        # f.write(f"h1={h1},\n")  
        # f.write(f"w2={w2},\n")  
        # f.write(f"h2={h2},\n")  
        # f.write(f"l={ll},\n")  
        # f.write(f"R0={0.99},\n")  
        # f.write(f"Qc={0.0219},\n")  
        # f.write(f"alpha={6.07},\n")  
        # f.write(f"d=0,\n")
        # f.write(f"mx={2},\n")  
        # f.write(f"my={2}\n")  
        # f.write(")\n")  
        # f.write(f"AT (0, 0, {location}) RELATIVE  origin\n\n")

        # Guide_gravity 定义 guide_channel 的位置和参数  
        f.write(f"COMPONENT Guide_section{i+1} = Guide_gravity (\n")  
        f.write(f"w1={w1},\n")  
        f.write(f"h1={h1},\n")  
        f.write(f"w2={w2},\n")  
        f.write(f"h2={h2},\n")  
        f.write(f"l={ll},\n")  
        f.write(f"R0={0.99},\n")  
        f.write(f"Qc={0.0219},\n")  
        f.write(f"alpha={6.07},\n")  
        f.write(f"d=0,\n")
        f.write(f"m={2},\n")  
        f.write(f"G=0\n")
        f.write(")\n")  
        f.write(f"AT (0, 0, {location}) RELATIVE  origin\n\n")

    endloc = location + ll
    # psd Monitor
    f.write(f"COMPONENT 2dmon = Monitor_nD(\n")
    f.write(f'options = "x bins=100 y bins=100",\n')
    f.write(f"xwidth = 0.04,\n")
    f.write(f"yheight = 0.08\n")
    f.write(")\n")  
    f.write(f"AT (0, 0, {zmax * 0.001 +0.2}) RELATIVE  origin\n\n")

    # psd x Monitor
    f.write(f"COMPONENT x_mon_exit = Monitor_nD(\n")
    f.write(f'options = "x bins=101",\n')
    f.write(f"xwidth = 0.04,\n")
    f.write(f"yheight = 0.08\n")
    f.write(")\n")  
    f.write(f"AT (0, 0, {zmax * 0.001 +0.2}) RELATIVE  origin\n\n")

    # psd y Monitor
    f.write(f"COMPONENT y_mon_exit = Monitor_nD(\n")
    f.write(f'options = "y bins=100",\n')
    f.write(f"xwidth = 0.04,\n")
    f.write(f"yheight = 0.08\n")
    f.write(")\n")  
    f.write(f"AT (0, 0, {zmax * 0.001 +0.2}) RELATIVE  origin\n\n")

    # energy Monitor
    f.write(f"COMPONENT eng_exit_Monitor = Monitor_nD(\n")
    f.write(f'options = "log energy, limits=[-1 5], bins=100",\n')
    f.write(f"xwidth = 0.04,\n")
    f.write(f"yheight = 0.08\n")
    f.write(")\n")  
    f.write(f"AT (0, 0, {zmax * 0.001 +0.2}) RELATIVE  origin\n\n")

    # 文件尾部  
    f.write("END\n")  

print(f"生成 {num_channels} 个 guide_channel 的脚本已保存为 {output_file}.")  