#!/usr/bin/env python3
"""
Example demonstrating CinemaXYZ usage for 2D data analysis.

This example shows:
1. Creating and filling a 2D histogram
2. Converting to CinemaXYZ for error propagation
3. Basic mathematical operations
4. Different visualization methods
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from Cinema.Prompt.histogram import Hist2D
from Cinema.Interface import CinemaXYZ

def create_test_histogram(N=100000):
    """Create a 2D histogram with gaussian-weighted random data.
    
    Args:
        N: Number of points to generate
    Returns:
        Hist2D object filled with gaussian-weighted random data
    """
    # Initialize histogram
    xbin, ybin = 20, 20
    xmin, xmax = 0., 1.
    ymin, ymax = 0., 1.
    hist2d = Hist2D(xmin, xmax, xbin, ymin, ymax, ybin)
    
    # Generate gaussian-weighted random data
    x = np.random.random(N)
    y = np.random.random(N)
    weights = np.exp(-(x-0.5)**2/0.1 - (y-0.5)**2/0.1)
    hist2d.fillmany(x, y, weights)
    
    return hist2d

def plot_basic_visualizations(data2d):
    """Create basic visualization plots: original, scaled and 3D surface.
    
    Args:
        data2d: CinemaXYZ instance to visualize
    """
    fig = plt.figure(figsize=(15, 5))
    
    # Original 2D heatmap
    ax1 = fig.add_subplot(131)
    data2d.plot(ax=ax1, cmap='viridis')
    ax1.set_title('Original Data')
    
    # Scaled data (×2)
    ax2 = fig.add_subplot(132)
    (data2d * 2).plot(ax=ax2, cmap='viridis')
    ax2.set_title('Scaled Data (×2)')
    
    # 3D surface view
    ax3 = fig.add_subplot(133, projection='3d')
    data2d.plot_surface(ax=ax3, cmap='viridis')
    ax3.set_title('3D Surface Plot')
    
    plt.tight_layout()

def plot_error_analysis(data2d):
    """Create error analysis plots: standard deviation and relative error.
    
    Args:
        data2d: CinemaXYZ instance to analyze
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    
    # Standard deviation
    data2d.plot(ax=ax1, plot_errors=True, cmap='viridis')
    ax1.set_title('Standard Deviation')
    
    # Relative error
    relative_error = data2d.sdev / data2d.mean
    extent = [data2d.x[0], data2d.x[-1], data2d.y[0], data2d.y[-1]]
    im = ax2.imshow(relative_error, origin='lower', aspect='auto', 
                    extent=extent, cmap='viridis')
    plt.colorbar(im, ax=ax2, label='Relative Error')
    ax2.set_title('Relative Error')
    
    plt.tight_layout()

def main():
    # Create and fill histogram
    hist2d = create_test_histogram()
    
    # Convert to CinemaXYZ array
    xedges, yedges = hist2d.getEdges()
    data2d = CinemaXYZ.from_hist2d(hist2d)
    
    # Create visualizations
    plot_basic_visualizations(data2d)
    plt.show()
    
    plot_error_analysis(data2d)
    plt.show()
    
    # Interpolation example - FIXED: Use bin centers instead of edges for interpolation
    # The issue was that edges extend beyond the data range, causing out-of-bounds errors
    new_x = np.linspace(data2d.x[0], data2d.x[-1], 50)  # Use data2d.x instead of xedges
    new_y = np.linspace(data2d.y[0], data2d.y[-1], 50)  # Use data2d.y instead of yedges
    data2d_interp = data2d.interpolate(new_x, new_y)
    
    # Compare original vs interpolated
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    data2d.plot(ax=ax1)
    ax1.set_title('Original Grid')
    data2d_interp.plot(ax=ax2)
    ax2.set_title('Interpolated Grid')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()