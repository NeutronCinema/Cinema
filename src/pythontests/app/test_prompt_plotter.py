#!/usr/bin/env python3

from Cinema.Prompt.cli.ptplotcli import IncidentParametersCfgStr, MCPLDataCfgStr


def test_plotter():
    a = IncidentParametersCfgStr.from_string("incident_energy_eV=123.45;incident_wavelength_A=1.234;incident_direction=(0.1,0.2,0.3);sample_position=(0.0,0.0,0.0)")
    print(a.to_dict())

    b = MCPLDataCfgStr.from_filestring("filename.mcpl;para=time;binmin=0;binmax=10;binnum=50;incident_params=[incident_energy_eV=123.45;incident_wavelength_A=1.234;incident_direction=(0.1,0.2,0.3);sample_position=(0.0,0.0,0.0)]")
    print(b.to_dict())
