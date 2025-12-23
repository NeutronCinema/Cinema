#ifndef Prompt_PythonGun_hh
#define Prompt_PythonGun_hh

#include "PTPrimaryGun.hh"
#include "PTStackManager.hh"

namespace Prompt {
  class PythonGun : public PrimaryGun {
  public:
    PythonGun(int pdg);
    virtual ~PythonGun(); 
    virtual std::unique_ptr<Particle> generate() override
    { PROMPT_THROW(CalcError, "std::unique_ptr<Particle> generate()  is not implemented"); };
    virtual void sampleEnergy(double &ekin) override 
    { PROMPT_THROW(CalcError, "SampleEnergy is not implemented"); };
    virtual void samplePosDir(Vector &pos, Vector &dir) override 
    { PROMPT_THROW(CalcError, "SamplePosDir is not implemented"); };

    void pushToStack(double *pdata);

  private:
      StackManager &m_stackManager;
  };
}



#ifdef __cplusplus
extern "C" {
#endif

  void* pt_PythonGun_new(int pdg);
  void pt_PythonGun_delete(void *obj);
  void pt_PythonGun_pushToStack(void *obj, double *pdata);
  void pt_PythonGun_pushToStackMany(void *obj, double *pdata, unsigned num);
  
#ifdef __cplusplus
}
#endif



#endif
