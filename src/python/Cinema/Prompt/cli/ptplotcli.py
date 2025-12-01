#!/usr/bin/env python3
"""
Script to load multiple HDF5 files using CinemaXY.from_hdf5 method and create plots
Supports individual plots and combined plots using "+" notation
"""

import sys
import os
import argparse
import numpy as np
import glob
import matplotlib.pyplot as plt  # Add global import
from Cinema.Interface import plotStyle
from Cinema.analysis import ParticleParameter
from dataclasses import dataclass, fields
from typing import Optional, Union, Literal
from Cinema.analysis import IncidentParameters
plotStyle()

try:
    from Cinema import CinemaXY
    print("Successfully imported CinemaXY class")
except ImportError as e:
    print(f"Failed to import CinemaXY class: {e}")
    sys.exit(1)

@dataclass
class _ParticleParameterCfgStr:
    """
    Config String Parser for incident parameters
    """

    @classmethod
    def from_string(cls, file_config_string):
        if not isinstance(file_config_string, str):
            raise TypeError("Must be a string")

        # Split by separator
        parts = file_config_string.split(";")
        if '' in parts:
            parts.remove('')

        para_dict = {}

        # Parse parameters from the remaining parts
        for item in parts[0:]:
            if '=' not in item:
                raise ValueError(f"ERROR: wrong format in parameter: {item}, use 'key=value' instead")
            else:
                key, value = item.split('=', 1)
                para_dict[key.strip()] = value.strip()
        
        # Check for unknown parameters
        valid_fields = {field.name for field in fields(cls)}
        for param_name in para_dict.keys():
            if param_name not in valid_fields:
                valid_params_str = ", ".join(valid_fields)
                raise ValueError(
                    f"ERROR: unknown parameter: '{param_name}'\n"
                    f"Valid parameters are: {valid_params_str}"
                )
        
        return cls(**para_dict)
    

    def _validate(self, v, typeconvert : type, exceptions=[], exception_only = False):
        errmsg = f"ERROR: invalid value: '{v}'\nValid values are: '{', '.join(exceptions)}' or type {typeconvert.__name__}"
        if v in exceptions:
            return v
        if exception_only:
            raise ValueError(errmsg)
        
        try:
            v = typeconvert(v)
            return v
        except ValueError:
            raise ValueError(errmsg)
        
    def to_dict(self):
        """Return dictionary representation of the config"""
        return self.__dict__

@dataclass
class IncidentParametersCfgStr(_ParticleParameterCfgStr):
    """
    Config String Parser for incident parameters
    
    This class parses configuration strings in the format:
    "incident_energy_eV=123.45;incident_wavelength_A=1.234;incident_direction=(0.1,0.2,0.3);sample_position=(0.0,0.0,0.0)"
    
    """
    incident_energy_eV: Optional[float] = None
    incident_wavelength_A: Optional[float] = None
    incident_direction: Optional[np.ndarray] = None
    sample_position: Optional[np.ndarray] = None

    


@dataclass
class MCPLDataCfgStr(_ParticleParameterCfgStr):
    """
    Config String Parser for loading MCPL data
    
    This class parses configuration strings in the format:
    "filename.mcpl;x=time;bmin=0;bmax=10;bnum=50;
    incident_params=[incident_energy_eV=123.45;incident_wavelength_A=1.234;incident_direction=(0.1,0.2,0.3);sample_position=(0.0,0.0,0.0)]"
    
    """

    filename: str
    para: Optional[str] = "time"
    unit: Optional[str] = None
    binmin: Optional[Union[Literal["auto"], float]] = "auto"  
    binmax: Optional[Union[Literal["auto"], float]] = "auto"
    binnum: Optional[int] = 100
    incident_params: Optional[str] = None

    @staticmethod
    def extract_incident_params(config_string):
        if not isinstance(config_string, str):
            raise TypeError("Config string must be a string type")
        
        start_keyword = "incident_params=["
        start_idx = config_string.find(start_keyword)
        
        if start_idx == -1:
            return None
        
        start_idx += len(start_keyword) - 1 
        
        bracket_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(config_string)):
            char = config_string[i]
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            raise ValueError("incident_params: unmatched square brackets")
        
        incident_params = config_string[start_idx:end_idx + 1]
        
        return incident_params

    @classmethod
    def from_filestring(cls, file_config_string):
        """Create MCPLDataCfgStr from string format"""
        if not isinstance(file_config_string, str):
            raise TypeError("Must be a string")
        
        para_dict = {}

        # Extract incident_params first
        incident_params_str = cls.extract_incident_params(file_config_string)
        if incident_params_str:
            # Remove incident_params from the main string
            file_config_string = file_config_string.replace(incident_params_str, '')
            file_config_string = file_config_string.replace("incident_params=", "")
            para_dict['incident_params'] = incident_params_str[1:-1] # remove the square brackets


        # Split by separator
        parts = file_config_string.split(";")
        if '' in parts:
            parts.remove('')

        filename = parts[0]

        if filename.endswith('.h5'):
            raise ValueError(f"ERROR: .h5 files with ; mechanism is not implemented. Got: {file_config_string}")
        
        para_dict['filename'] = filename
        
        # Parse parameters from the remaining parts
        for item in parts[1:]:
            if '=' not in item:
                raise ValueError(f"ERROR: wrong format in parameter: {item}, use 'key=value' instead")
            else:
                key, value = item.split('=', 1)
                para_dict[key.strip()] = value.strip()

        # Check for unknown parameters
        valid_fields = {field.name for field in fields(cls)}
        for param_name in para_dict.keys():
            if param_name not in valid_fields:
                valid_fields.remove('filename') # filename is not a parameter
                valid_params_str = ", ".join(valid_fields)
                raise ValueError(
                    f"ERROR: unknown parameter: '{param_name}'\n"
                    f"Valid parameters are: {valid_params_str}"
                )
        
        return cls(**para_dict)
    

    def __post_init__(self):
           
        self.para = self._validate(self.para, str, 
                           [v.value for k,v in ParticleParameter.__members__.items()], 
                           exception_only=True)
        self.binmin = self._validate(self.binmin, float, ["auto"])
        self.binmax = self._validate(self.binmax, float, ["auto"])
        self.binnum = self._validate(self.binnum, int, [])


    

def load_single_h5_file(h5_filepath):
    """
    Load a single HDF5 file and return CinemaXY object with statistics
    
    Args:
        h5_filepath (str): Path to HDF5 file
        
    Returns:
        tuple: (CinemaXY object, file_basename) or (None, None) if failed
    """
    try:
        # Check if file exists
        if not os.path.exists(h5_filepath):
            print(f"Error: File {h5_filepath} does not exist")
            return None, None
        
        print(f"\nLoading HDF5 file: {h5_filepath}")
        
        # Use the from_hdf5 method you implemented
        cinema_data = CinemaXY.from_hdf5(h5_filepath)
        
        file_basename = os.path.basename(h5_filepath)
        print(f"Successfully created CinemaXY object for {file_basename}")
        print(f"Data shape: {cinema_data.shape}")
        print(f"X coordinate range: [{cinema_data.x.min():.3f}, {cinema_data.x.max():.3f}]")
        print(f"Weight range: [{cinema_data.mean.min():.3f}, {cinema_data.mean.max():.3f}]")
        print(f"Standard deviation range: [{cinema_data.sdev.min():.3f}, {cinema_data.sdev.max():.3f}]")
        
        return cinema_data, file_basename
        
    except Exception as e:
        print(f"Error processing HDF5 file {h5_filepath}: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def load_single_mcpl_file(mcplfilepath, **kwargs):
    from Cinema.analysis import MCPL_Analyzer_1D

    try:
        # Check if file exists
        if not os.path.exists(mcplfilepath):
            print(f"Error: File {mcplfilepath} does not exist")
            return None, None
        
        print(f"\nLoading MCPL file: {mcplfilepath}")
        if kwargs.get('binmin') == 'auto'or kwargs.get('binmax') == 'auto':
            analyser = MCPL_Analyzer_1D(**kwargs, auto_range_file=mcplfilepath)
        else:
            analyser = MCPL_Analyzer_1D(**kwargs)
        analyser.analyze(mcplfilepath)

        cinema_data = analyser.toArrayXY()
        file_basename = os.path.basename(mcplfilepath)
        print(f"Successfully created CinemaXY object for {file_basename}")
        print(f"Data shape: {cinema_data.shape}")
        print(f"X coordinate range: [{cinema_data.x.min():.3f}, {cinema_data.x.max():.3f}]")
        print(f"Weight range: [{cinema_data.mean.min():.3f}, {cinema_data.mean.max():.3f}]")
        print(f"Standard deviation range: [{cinema_data.sdev.min():.3f}, {cinema_data.sdev.max():.3f}]")
        print(f"Parameters: {kwargs}")
        
        return analyser, file_basename
        
    except Exception as e:
        print(f"Error processing MCPL file {mcplfilepath}: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def calculate_integral(cinema_data):
    """Calculate the integral of CinemaXY curve
    as the it is the histogram data, the sum of mean values is the integral"""
    return np.sum(cinema_data.mean) 

def format_integral_value(integral):
    """
    Format integral value for display based on its magnitude
    
    Args:
        integral (float): The integral value to format
        
    Returns:
        str: Formatted integral string
    """
    if integral >= 1e6:
        return f"{integral:.2e}"
    elif integral >= 1000:
        return f"{integral:.0f}"
    elif integral >= 1:
        return f"{integral:.2f}"
    else:
        return f"{integral:.4f}"

def create_combined_plot(cinema_data_list : list[CinemaXY], 
                         file_basenames, xlabel=None, output_image=None, downbinning_level=0):
    """
    Create a combined plot for multiple CinemaXY objects
    
    Args:
        cinema_data_list: List of CinemaXY objects
        file_basenames (list): List of base names for each file
        output_image (str): Output image file path (optional)
        
    Returns:
        matplotlib.figure.Figure: The created figure
    """
    # Remove internal import, use global plt
    # Create a figure for combined plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Define colors and markers for different files
    colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']
    markers = ['o', 's', '^', 'D', 'v', '<', '>']
    
    for i, (cinema_data, basename) in enumerate(zip(cinema_data_list, file_basenames)):

        color = colors[i % len(colors)]
        marker = markers[i % len(markers)]
        
        # Calculate integral
        integral = calculate_integral(cinema_data)
        # Downbinning
        for _ in range(downbinning_level):
            cinema_data = (cinema_data[::2] + cinema_data[1::2])

        # Format integral value display using the new function
        integral_str = format_integral_value(integral)
        
        # Use CinemaXY's built-in plot method with different styles
        alpha = 0.4 if i == 0 else 1.0
        cinema_data.plot(ax=ax, fmt=f'{color}-', marker=marker, markersize=3, alpha=alpha,
                       label=f'{basename} ± Std Dev, integral {integral_str}', capsize=3, elinewidth=1)
    
    # Set axis labels
    ax.set_xlabel(xlabel if xlabel else 'X Coordinate')
    ax.set_ylabel('Weight')
    # ax.set_title('Combined HDF5 Data Visualization')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save image
    if output_image:
        plt.savefig(output_image, dpi=300, bbox_inches='tight')
        print(f"Combined plot saved to: {output_image}")
    
    return fig

def create_individual_plot(cinema_data : CinemaXY, file_basename, xlabel=None, output_image=None, downbinning_level=0):
    """
    Create an individual plot for a single CinemaXY object
    
    Args:
        cinema_data: CinemaXY object
        file_basename (str): Base name of the file for title
        output_image (str): Output image file path (optional)
        
    Returns:
        matplotlib.figure.Figure: The created figure
    """
    # Remove internal import, use global plt
    # Create a figure for this file
    fig, ax = plt.subplots(figsize=(10, 6))
    # Calculate integral
    integral = calculate_integral(cinema_data)
    
    # Downbinning
    for _ in range(downbinning_level):
        cinema_data = (cinema_data[::2] + cinema_data[1::2])

    # Format integral value display using the new function
    integral_str = format_integral_value(integral)
    
    # Use CinemaXY's built-in plot method
    cinema_data.plot(ax=ax, fmt='b-', marker='o', markersize=4, 
                   label=f'Weight ± Standard Deviation, integral {integral_str}', capsize=3, elinewidth=1)
    # Set axis labels
    ax.set_xlabel(xlabel if xlabel else 'X Coordinate')
    ax.set_ylabel('Weight')
    ax.set_title(f'HDF5 Data Visualization (File: {file_basename})')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save image with filename-based naming if output directory is specified
    if output_image:
        # If output_image is a directory, create filename based on input file
        if os.path.isdir(output_image):
            output_dir = output_image
            # Create output filename: remove .h5 extension and add .png
            output_filename = file_basename.replace('.h5', '.png')
            output_path = os.path.join(output_dir, output_filename)
        else:
            # If single file specified, use it for the first file only
            output_path = output_image
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_path}")
    
    return fig

def parse_file_groups(file_patterns):
    """
    Parse file patterns and return a list of dictionaries with file information.
    
    Args:
        file_patterns (list): List of file paths, glob patterns, or combined groups using "+" notation
        
    Returns:
        list: List of dictionaries, each containing:
            - 'filepath': Full file path
            - 'xpara': X parameter (default "time")
            - 'binmin': Minimum bin value (optional)
            - 'binmax': Maximum bin value (optional)
            - 'binnum': Number of bins (optional)
    """
    
    def _individual_parse(ind_pattern):
        file_dicts = []
        parsed_dict = {}
        # Parse mcpl file string to extract filename and parameters
        if ';' in ind_pattern:
            parsed_dict = MCPLDataCfgStr.from_filestring(ind_pattern).to_dict()
        else:
            parsed_dict.update({'filename': ind_pattern}) # update on parsed_dict will act on the class behind: MCPLDataConfig
        filename = parsed_dict.get('filename', None)

        if '*' in filename or '?' in filename:
            # This is a glob pattern
            matched_files = glob.glob(filename)
            for filepath in matched_files:
                parsed_dict.update({'filename': filepath})
                status_pdict = parsed_dict.copy() # avoid modify original dict
                file_dicts.append(status_pdict)
        else:
            # This is a specific file path
            if os.path.exists(filename):
                status_pdict = parsed_dict.copy() # avoid modify original dict
                file_dicts.append(status_pdict)
            else:
                print(f"Warning: File '{filename}' does not exist")
        return file_dicts
    
    groups = []
    dictgroup = []
    for pattern in file_patterns:
        pattern = pattern.strip()
        # if any([sep in pattern for sep in COM_SEPARATOR]):
        #     raise ValueError(f"ERROR: wrong separator in pattern: {pattern}, use ';' instead'")

        # Check if this is a combined pattern (contains "+")
        if '+' in pattern:
            # Split by "+" to get individual patterns
            individual_patterns = pattern.split('+')
            
            for individual_pattern in individual_patterns:
                dictgroup.extend(_individual_parse(individual_pattern))
            print(f"\nProcessed combined pattern: {pattern}")
        else:
            # This is a single file or glob pattern
            # Parse mcpl file string to extract filename and parameters
            dictgroup = _individual_parse(pattern)
        groups.append(dictgroup)
    return groups

def load_and_plot_files(file_patterns, output_dir=None, show_plot=True, downbinning_level=0):
    """
    Load HDF5 files and create plots with support for combined plotting
    
    Args:
        file_patterns (list): List of file paths, glob patterns, or combined groups
        output_dir (str): Output directory for saving plots (optional)
        show_plot (bool): Whether to display plots
        downbinning_level (int): Downbinning level (0=no downbinning, 1=downbinning once, etc.)
        
    Returns:
        bool: True if all files processed successfully, False otherwise
    """
    # Parse file groups - now returns a list of dictionaries
    file_dicts = parse_file_groups(file_patterns)
    if not file_dicts:
        print("No valid HDF5 or MCPL files found to process")
        return False
    
    print(f"\nProcessing {len(file_dicts)} file groups:")
    for i, group in enumerate(file_dicts, 1):
        if len(group) == 1:
            file_dict = group[0]
            print(f"  {i}. Individual: {file_dict.get('filename', None)} ")
        else:
            file_list = [f['filename'] for f in group]
            print(f"  {i}. Combined: {' + '.join([os.path.basename(f) for f in file_list])}")
    
    success_count = 0
    all_figures = []  # Store all figures to show at once
    
    for i, file_group in enumerate(file_dicts, 1):
        print(f"\n--- Processing group {i}/{len(file_dicts)} ---")
        
        # Load all files in this group
        cinema_data_list = []
        file_basenames = []
        
        xlabel = 'X coordinate'
        for file_dict in file_group:

            filepath = file_dict.get('filename', None)
            kwargs = {k: v for k, v in file_dict.items() if k not in ['filename']}
            
            if filepath.endswith('.h5'):
                cinema_data, file_basename = load_single_h5_file(filepath)
            elif filepath.endswith('.mcpl') or filepath.endswith('.mcpl.gz'):
                # Pass parameters to load_single_mcpl_file
                analyser, file_basename = load_single_mcpl_file(filepath, **kwargs)
                cinema_data = analyser.toArrayXY()
                xlabel = analyser.label_axis
            
            if cinema_data is None:
                print(f"Failed to process file: {filepath}")
                continue
            
            cinema_data_list.append(cinema_data)
            file_basenames.append(file_basename)

        if not cinema_data_list:
            print(f"No valid data loaded for group {i}")
            continue
        
        # Create appropriate plot type
        if len(cinema_data_list) == 1:
            # Individual plot
            fig = create_individual_plot(
                cinema_data_list[0], 
                file_basenames[0],
                output_image=output_dir,
                xlabel=xlabel,
                downbinning_level=downbinning_level
            )
            all_figures.append(fig)
            
            # Calculate and display integral
            integral = calculate_integral(cinema_data_list[0])
            integral_str = format_integral_value(integral)  # Use the new function
            
            # Print statistics for this file
            print(f"\nStatistics for {file_basenames[0]}:")
            print(f"  Data points: {len(cinema_data_list[0].x)}")
            print(f"  Weight range: [{cinema_data_list[0].mean.min():.6f}, {cinema_data_list[0].mean.max():.6f}]")
            print(f"  Std dev range: [{cinema_data_list[0].sdev.min():.6f}, {cinema_data_list[0].sdev.max():.6f}]")
            print(f"  Curve integral: {integral:.6f}")
            
        else:
            # Combined plot
            combined_name = "+".join([os.path.basename(f.get('filename', None)).replace('.h5', '') for f in file_group])
            output_path = None
            if output_dir and os.path.isdir(output_dir):
                output_path = os.path.join(output_dir, f"combined_{combined_name}.png")

            fig = create_combined_plot(
                cinema_data_list,
                file_basenames,
                xlabel=xlabel,
                output_image=output_path,
                downbinning_level=downbinning_level
            )
            all_figures.append(fig)
            
            # Display integrals for each file
            print(f"\nIntegrals for combined plot {combined_name}:")
            for cinema_data, basename in zip(cinema_data_list, file_basenames):
                integral = calculate_integral(cinema_data)
                integral_str = format_integral_value(integral)  # Use the new function
                print(f"  {basename}: {integral_str}")
        
        success_count += 1
    
    # Show all plots at once if requested
    if show_plot and all_figures:
        # plt.xscale('log')
        plt.yscale('log')
        plt.show()  # Now plt is defined in global scope
    
    print(f"\nSuccessfully processed {success_count}/{len(file_dicts)} file groups")
    return success_count == len(file_dicts)

def main():
    """Main function"""
    # Create the argument parser with usage examples in the epilog
    parser = argparse.ArgumentParser(
        description='Load HDF5 files using CinemaXY.from_hdf5 and create plots with combined plotting support',
        epilog='''
Examples:
  ptplot file1.h5 file2.h5
  ptplot *.h5
  ptplot monitor1_TOF.h5+monitor2_TOF.h5
  ptplot data/*.h5 -o plots/
  ptplot "monitor*_MCPL.mcpl;para=time;binmin=0;binmax=10;binnum=100+"
  ptplot "detMCPL_scat_*_pro0.mcpl;para=scattering_angle;unit=deg;binmin=0;binmax=180;binnum=1800;incident_params=[incident_wavelength_A=4;incident_direction=(0,0,1);sample_position=(0.0,0.0,0.0)]
  ptplot --help
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input_files', nargs='+', 
                       help='Input HDF5 file paths, glob patterns, or combined groups using "+" notation')
    parser.add_argument('-o', '--output', help='Output directory for saving plots (optional)')
    parser.add_argument('--no-show', action='store_true', help='Do not display plot windows')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('-d', '--downbinning', action='count', default=0,
                       help='Downbinning data: -d for once, -dd for twice, -ddd for three times')
    args = parser.parse_args()
    
    # Run main function
    success = False
    try:
        success = load_and_plot_files(
            args.input_files,
            output_dir=args.output,
            show_plot=not args.no_show,
            downbinning_level=args.downbinning
        )
    except Exception as e:
        print(f"\nError message: {e}")
        if args.debug:
            raise e
    
    if success:
        print("\n✅ Processing completed successfully!")
    else:
        print("\n❌ Processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    # If no arguments provided, use default file pattern
    if len(sys.argv) == 1:
        default_pattern = '*.h5'
        matched_files = glob.glob(default_pattern)
        if matched_files:
            print(f"Found {len(matched_files)} HDF5 files matching pattern '{default_pattern}':")
            for filepath in matched_files:
                print(f"  {filepath}")
            success = load_and_plot_files([default_pattern])
        else:
            # Show help when no files found
            import sys
            sys.argv.append('--help')
            main()
    else:
        main()