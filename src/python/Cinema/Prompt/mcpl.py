from mcpl import MCPLFile
import numpy as np

class PTMCPL:
    """
    Enhanced MCPL file reader with new data structure access.
    
    This class wraps MCPLFile and provides convenient methods for accessing
    particle data with the new field structure:
    - userflags: eventID (uint32)
    - polarisation[0]: survival_probability (double)
    - polarisation[1]: scatteringNumber (double) 
    - polarisation[2]: differentialEnergy (double)
    
    Example usage:
    
    ```python
    from Cinema.Prompt import PTMCPL
    from Cinema.Prompt.histogram import Hist1D
    import numpy as np
    
    # Load MCPL file and analyze survival probabilities
    fn = 'detMCPL_scat_pro0.mcpl'
    hist_E = Hist1D(xmin=1e-6, xmax=4e-2, num=500)
    hist_E_sgl = Hist1D(xmin=1e-6, xmax=4e-2, num=500)
    
    file = PTMCPL(fn)
    sum = 0.0        
    sgl_elast = 0.
    sgl_inelast = 0.
    mul_scatt = 0.
    
    for pb in file.particle_blocks:
        survP = pb.survival_probability
        sgl_elast += np.sum(pb.getSingleElasticScatteringWeight()* survP)
        sgl_inelast += np.sum(pb.getSingleInelasticScatteringWeight()* survP)
        mul_scatt += np.sum(pb.getMultipleScatteringWeight()* survP)
        sum += np.sum(survP * pb.weight)
        hist_E.fill(pb.differential_energy, survP * pb.weight)
        hist_E_sgl.fill(pb.differential_energy, survP * pb.weight *pb.single_scattering_flags)
    
    print(f"Total sum: {sum}, offset: {sum - sgl_elast - sgl_inelast - mul_scatt}")
    print(f"Single elastic sum: {sgl_elast}")
    print(f"Single inelastic sum: {sgl_inelast}")
    print(f"Multiple scatter sum: {mul_scatt}")
    
    # Visualize results
    hist_E_sgl.plot()
    hist_E.plot(show=True)
    ```
    
    This example demonstrates how to analyze survival probabilities and 
    categorize scattering events by type (single elastic, single inelastic, multiple).
    """
    
    def __init__(self, filename: str, blocklength: int = 10000):
        """
        Initialize the PTMCPL file reader.
        
        Args:
            filename: Path to the MCPL file to read
            blocklength: Number of particles per block (default: 10000)
            
        Example:
            >>> file = PTMCPL('simulation_output.mcpl')
            >>> for block in file.particle_blocks:
            ...     print(f"Block with {len(block.ekin)} particles")
        """
        self._mcpl_file = MCPLFile(filename, blocklength)
        self.filename = filename
    
    @property
    def particle_blocks(self):
        """
        Get particle blocks with enhanced functionality.
        
        Returns:
            PTParticleBlockIterator: Iterator over particle blocks with additional methods
        """
        return PTParticleBlockIterator(self._mcpl_file.particle_blocks)
    
    def __iter__(self):
        """Iterate over particle blocks."""
        return iter(self.particle_blocks)
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        # MCPLFile doesn't need explicit closing in current implementation
        pass


class PTParticleBlockIterator:
    """
    Enhanced iterator for particle blocks with additional convenience methods.
    """
    
    def __init__(self, particle_blocks):
        """
        Initialize the enhanced particle block iterator.
        
        Args:
            particle_blocks: Original particle blocks iterator from MCPLFile
        """
        self._particle_blocks = particle_blocks
    
    def __iter__(self):
        """Iterate over particle blocks with enhanced functionality."""
        for pb in self._particle_blocks:
            yield PTParticleBlock(pb)
    
    def __next__(self):
        """Get next particle block with enhanced functionality."""
        return PTParticleBlock(next(self._particle_blocks))


class PTParticleBlock:
    """
    Enhanced particle block with new data structure access.
    
    New field structure:
    - userflags: eventID (uint32)
    - polarisation[0]: survival_probability (double)
    - polarisation[1]: scatteringNumber (double)
    - polarisation[2]: differentialEnergy (double)
    """
    
    def getSingleElasticScatteringWeight(self) -> np.ndarray:
        """
        Get weights for single elastic scattering events.
        
        Returns:
            np.ndarray: Array of weights for single elastic scattering
            
        Example:
            >>> for pb in file.particle_blocks:
            ...     elastic_weights = pb.getSingleElasticScatteringWeight()
            ...     weighted_sum = np.sum(elastic_weights * pb.survival_probability)
        """
        single_flags = self.getSingleScatteringFlags()
        elastic_flags = self.getElasticFlags()
        return (single_flags & elastic_flags).astype(float) * self.weight
    
    def getSingleInelasticScatteringWeight(self) -> np.ndarray:
        """
        Get weights for single inelastic scattering events.
        
        Returns:
            np.ndarray: Array of weights for single inelastic scattering
        """
        single_flags = self.getSingleScatteringFlags()
        inelastic_flags = self.getInelasticFlags()
        return (single_flags & inelastic_flags).astype(float) * self.weight
    
    def getMultipleScatteringWeight(self) -> np.ndarray:
        """
        Get weights for multiple scattering events.
        
        Returns:
            np.ndarray: Array of weights for multiple scattering
        """
        multiple_flags = self.getMultipleScatteringFlags()
        return multiple_flags.astype(float) * self.weight
    
    def __init__(self, particle_block):
        """
        Initialize the enhanced particle block.
        
        Args:
            particle_block: Original particle block from MCPLFile
        """
        self._particle_block = particle_block
    
    def __getattr__(self, name):
        """
        Delegate attribute access to the underlying particle block.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute value from underlying particle block
        """
        return getattr(self._particle_block, name)
    
    def getEventID(self) -> np.ndarray:
        """
        Get the event ID for particles in this block.
        
        Returns:
            np.ndarray: Array of event IDs for each particle (uint32)
        """
        return np.array(self._particle_block.userflags, dtype=np.uint32)
    
    def getSurvivalProbability(self) -> np.ndarray:
        """
        Get the survival probability for particles in this block.
        
        Returns:
            np.ndarray: Array of survival probabilities for each particle (double)
        """
        if not hasattr(self._particle_block, 'polarisation'):
            raise AttributeError("polarisation field is not available in this MCPL file")
        
        polarisation = np.array(self._particle_block.polarisation)
        if polarisation.ndim == 1:
            polarisation = polarisation.reshape(-1, 3)
        
        return polarisation[:, 0]  # polarisation[0] is survival probability
    
    def getScatteringNumber(self) -> np.ndarray:
        """
        Get the scattering number for particles in this block.
        
        Returns:
            np.ndarray: Array of scattering numbers for each particle (double)
        """
        if not hasattr(self._particle_block, 'polarisation'):
            raise AttributeError("polarisation field is not available in this MCPL file")
        
        return np.array(self._particle_block.poly).astype(np.int32)

    def getDifferentialEnergy(self) -> np.ndarray:
        """
        Get the differential energy for particles in this block.
        
        Returns:
            np.ndarray: Array of differential energies for each particle (double)
        """
        if not hasattr(self._particle_block, 'polarisation'):
            raise AttributeError("polarisation field is not available in this MCPL file")
        
        return np.array(self._particle_block.polz)
        
    def getSingleScatteringFlags(self) -> np.ndarray:
        """
        Get flags indicating if particles are single scattered (scatteringNumber == 1).
        
        Returns:
            np.ndarray: Boolean array indicating single scattering for each particle
        """
        scattering_numbers = self.getScatteringNumber()
        return scattering_numbers == 1
    
    def getElasticFlags(self) -> np.ndarray:
        """
        Get flags indicating if particles are elastic (differentialEnergy == 0).
        
        Returns:
            np.ndarray: Boolean array indicating elastic scattering for each particle
        """
        differential_energies = self.getDifferentialEnergy()
        return differential_energies == 0.
    
    def getInelasticFlags(self) -> np.ndarray:
        """
        Get flags indicating if particles are inelastic (differentialEnergy != 0).
        
        Returns:
            np.ndarray: Boolean array indicating inelastic scattering for each particle
        """
        differential_energies = self.getDifferentialEnergy()
        return differential_energies != 0.
    
    @property
    def inelastic_flags(self) -> np.ndarray:
        """
        Property access to inelastic scattering flags.
        
        Returns:
            np.ndarray: Boolean array indicating inelastic scattering for each particle
        """
        return self.getInelasticFlags()
    
    def getMultipleScatteringFlags(self) -> np.ndarray:
        """
        Get flags indicating if particles are multiple scattered (scatteringNumber > 1).
        
        Returns:
            np.ndarray: Boolean array indicating multiple scattering for each particle
        """
        scattering_numbers = self.getScatteringNumber()
        return scattering_numbers > 1
    
    @property
    def multiple_scattering_flags(self) -> np.ndarray:
        """
        Property access to multiple scattering flags.
        
        Returns:
            np.ndarray: Boolean array indicating multiple scattering for each particle
        """
        return self.getMultipleScatteringFlags()
    
    def getSingleElasticScatteringWeight(self) -> np.ndarray:   
        """
        Get weights for single elastic scattered particles.
        
        Returns:
            np.ndarray: Weights for single elastic scattered particles
        """
        elastic_flags = self.getElasticFlags()
        single_scattering_flags = self.getSingleScatteringFlags()
        weights = np.array(self._particle_block.weight)
        
        return elastic_flags * single_scattering_flags * weights 
    

    def getSingleInelasticScatteringWeight(self) -> np.ndarray:   
        """
        Get weights for single inelastic scattered particles.
        
        Returns:
            np.ndarray: Weights for single inelastic scattered particles
        """
        inelastic_flags = self.getInelasticFlags()
        single_scattering_flags = self.getSingleScatteringFlags()
        weights = np.array(self._particle_block.weight)
        
        return inelastic_flags * single_scattering_flags * weights 
    

    def getMultipleScatteringWeight(self) -> np.ndarray:   
        """
        Get weights for multiple scattered particles.
        
        Returns:
            np.ndarray: Weights for multiple scattered particles
        """
        multiple_scattering_flags = self.getMultipleScatteringFlags()
        weights = np.array(self._particle_block.weight)
        
        return multiple_scattering_flags * weights

    @property
    def elastic_flags(self) -> np.ndarray:
        """
        Property access to elastic scattering flags.
        
        Returns:
            np.ndarray: Boolean array indicating elastic scattering for each particle
        """
        return self.getElasticFlags()
    
    @property
    def single_scattering_flags(self) -> np.ndarray:
        """
        Property access to single scattering flags.
        
        Returns:
            np.ndarray: Boolean array indicating single scattering for each particle
        """
        return self.getSingleScatteringFlags()
    
    @property
    def event_id(self) -> np.ndarray:
        """
        Property access to event ID.
        
        Returns:
            np.ndarray: Array of event IDs for each particle
        """
        return self.getEventID()
    
    @property
    def survival_probability(self) -> np.ndarray:
        """
        Property access to survival probability.
        
        Returns:
            np.ndarray: Array of survival probabilities for each particle
        """
        return self.getSurvivalProbability()
    
    @property
    def scattering_number(self) -> np.ndarray:
        """
        Property access to scattering number.
        
        Returns:
            np.ndarray: Array of scattering numbers for each particle
        """
        return self.getScatteringNumber()
    
    @property
    def differential_energy(self) -> np.ndarray:
        """
        Property access to differential energy.
        
        Returns:
            np.ndarray: Array of differential energies for each particle
        """
        return self.getDifferentialEnergy()
    
    
    def __str__(self):
        """
        Display first 10 particles in the requested format.
        """
        return self._format_particles(10)
    
    def display_particles(self, count=10):
        """
        Display particles in the requested format.
        
        Args:
            count: Number of particles to display (default: 10)
        """
        print(self._format_particles(count))
    
    def _format_particles(self, count=10):
        """
        Format particles for display.
        
        Args:
            count: Number of particles to display
            
        Returns:
            str: Formatted particle information
        """
        if len(self._particle_block.ekin) == 0:
            return "PTParticleBlock (empty)"
        
        # Get particle data
        num_particles = len(self._particle_block.ekin)
        positions = np.array(self._particle_block.position)
        directions = np.array(self._particle_block.direction)
        energies = np.array(self._particle_block.ekin)
        times = np.array(self._particle_block.time)
        weights = np.array(self._particle_block.weight)
        pdg_codes = np.array(self._particle_block.pdgcode)
        event_ids = self.getEventID()
        survive_p = self.getSurvivalProbability()
        scatter_nums = self.getScatteringNumber()
        diff_energy = self.getDifferentialEnergy()
        
        # Reshape position and direction arrays to (N, 3) if they're flat
        if positions.ndim == 1:
            positions = positions.reshape(-1, 3)
        if directions.ndim == 1:
            directions = directions.reshape(-1, 3)
        
        
        # Build header
        output = []
        output.append("index  pdgcode   ekin[eV]       x[mm]      y[mm]     z[mm]       ux       uy      uz    time[s]     weight    eventID  survProb  scatN  diffE[eV]")
        
        # Display specified number of particles (or all if less than count)
        display_count = min(count, num_particles)
        
        for i in range(display_count):
            # Convert to Python native types for string formatting
            x_mm = float(positions[i, 0])
            y_mm = float(positions[i, 1])
            z_mm = float(positions[i, 2])
            ux = float(directions[i, 0])
            uy = float(directions[i, 1])
            uz = float(directions[i, 2])
            ekin_ev = float(energies[i])
            time_s = float(times[i])
            weight = float(weights[i])
            pdgcode = int(pdg_codes[i])
            event_id = int(event_ids[i])
            survival_prob = float(survive_p[i])
            scatter_num = int(scatter_nums[i])
            diff_energy_val = float(diff_energy[i])
            
            # Format the line according to the requested format
            line = f"{i:4d} {pdgcode:6d} {ekin_ev:15.4e} {x_mm:10.2f} {y_mm:10.2f} {z_mm:10.2f} {ux:8.2f} {uy:8.2f} {uz:7.2f} {time_s:10.3e} {weight:8.3f} {event_id:8d} {survival_prob:10.1e} {scatter_num:5d} {diff_energy_val:10.3e}"
            output.append(line)
        
        # Add total count information
        if num_particles > display_count:
            output.append(f"... and {num_particles - display_count} more particles")
        
        return "\n".join(output)
    
    def __repr__(self):
        """Return concise representation."""
        num_particles = len(self._particle_block.ekin) if len(self._particle_block.ekin) > 0 else 0
        return f"PTParticleBlock(particles={num_particles})"

    def __getattr__(self, name):
        """
        Delegate attribute access to the underlying particle block, but block access to old polarisation fields.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute value from underlying particle block
            
        Raises:
            AttributeError: If trying to access old polarisation fields
        """
        # Block access to old polarisation fields
        if name in ['polarisation', 'polx', 'poly', 'polz']:
            raise AttributeError(f"'{name}' field is no longer available. Use the new data structure: event_id, survival_probability, scattering_number, differential_energy")
        
        # Delegate all other attributes to the underlying particle block
        return getattr(self._particle_block, name)