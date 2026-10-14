#include "PTMCPLParticleReader.hh"

Prompt::MCPLParticleReader::MCPLParticleReader(const std::string &fn, bool repeat)
:MCPLBinary(fn), m_repeat(repeat)
{ 
    m_file_r = mcpl_open_file(fn.c_str());
    m_parNum = mcpl_hdr_nparticles(m_file_r);
    if(!m_parNum)
        PROMPT_THROW(BadInput, "MCPL file contains 0 particles: " + fn);
    m_with_extraUserUnsigned = mcpl_hdr_has_userflags(m_file_r);
    m_with_extra3double = mcpl_hdr_has_polarisation(m_file_r);
    m_using_double = mcpl_hdr_has_doubleprec(m_file_r);
    //  const mcpl_particle_t* mcpl_read(mcpl_file_t);

    std::cout << " MCPLGun finds " << m_parNum << " particles in the file " << fn << std::endl;
}


uint64_t Prompt::MCPLParticleReader::particleCount() const
{
    return m_parNum;
}

// MCPL unit system: kinetic energy in MeV:
double Prompt::MCPLParticleReader::getEnergy() const
{
    return m_particleInFile->ekin*Unit::MeV;
}

// MCPL unit system: time in milliseconds:
double Prompt::MCPLParticleReader::getTime() const
{
    return m_particleInFile->time*Unit::ms;
}

// MCPL unit system: position in centimeters
void Prompt::MCPLParticleReader::getPosition( Vector& pos) const
{
    pos.set(m_particleInFile->position[0]*Unit::cm, 
            m_particleInFile->position[1]*Unit::cm,
            m_particleInFile->position[2]*Unit::cm);
}

double Prompt::MCPLParticleReader::getWeight() const
{
    return m_particleInFile->weight;
}

void Prompt::MCPLParticleReader::getDirection( Vector& dir) const
{
     dir.set(m_particleInFile->direction[0], 
             m_particleInFile->direction[1],
             m_particleInFile->direction[2]);
}

int32_t Prompt::MCPLParticleReader::getPDG() const
{
    return m_particleInFile->pdgcode;
}

bool Prompt::MCPLParticleReader::readOneParticle() const
{
    pt_assert_always(m_parNum);
    m_particleInFile = const_cast< mcpl_particle_t *> (mcpl_read(m_file_r));
    bool eof = m_particleInFile ? false : true;
    if(!m_repeat && eof)
    {
        return false;
    }
    
    if(eof)
    {
        mcpl_rewind(m_file_r);
        m_particleInFile = const_cast< mcpl_particle_t *> (mcpl_read(m_file_r));
    }

    return true;
}
