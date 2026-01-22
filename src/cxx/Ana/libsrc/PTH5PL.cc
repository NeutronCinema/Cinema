#include "PTH5PL.hh"
#include "PTHDF5BinaryWrite.hh"
#include "PTParticle.hh"
#include "PTHist1D.hh"
#include <iostream>
#include <memory>

namespace Prompt {

H5PL::H5PL(const std::string &name, unsigned int pdg, int groupid, bool kill, bool compress) 
    :Scorer1D("H5PL_"+name, Scorer::ScorerType::ENTRY, std::make_unique<Hist1D>("H5PL_"+name, -2.5, 100.5, 103, true), pdg=pdg, groupid=groupid),
      m_kill(kill) 
{
    
    std::string filename = name + ".h5";
    m_writer = new HDF5BinaryWrite(filename, compress);
    m_writer->init("H5PL Data Source");
    m_writer->addHeaderComment("H5PL particle data with custom fields");
}

H5PL::~H5PL() {
    if (m_writer) {
        delete m_writer;
        m_writer = nullptr;
    }
}

void H5PL::score(Particle &particle) {
    if(!rightScorer(particle))
    return;

    if(m_scatterCounter==nullptr)
    {
     m_writer->write(particle, -3);
    }
    else
    m_writer->write(particle, m_scatterCounter->getScatNumber());

    m_hist->fill(m_scatterNumberRequired);
    if(m_kill)
        particle.kill(Particle::KillType::SCORE);


    
}

void H5PL::addCustomField(const std::string& fieldName, const std::string& dataType) {
    // This method allows adding custom fields to the HDF5 dataset
    // Implementation would map string dataType to HDF5 types
    // For now, this is a placeholder for future extension
}

} // namespace Prompt