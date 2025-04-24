
#include "PTPython.hh"
#include "PTGidiSetting.hh"

namespace pt = Prompt;

bool pt_Gidi_compiled()
{
    bool gidi_compiled = false;
    #ifdef ENABLE_GIDI
        gidi_compiled = true;
    #endif
    return gidi_compiled;
}

void* pt_GidiSetting_getInstance()
{
  return static_cast<void *>(std::addressof(pt::Singleton<pt::GidiSetting>::getInstance()));
}

double pt_GidiSetting_getGidiThreshold(void* obj)
{
    return static_cast<pt::GidiSetting *>(obj)->getGidiThreshold();
}

void pt_GidiSetting_setGidiThreshold(void* obj, double t)
{
    static_cast<pt::GidiSetting *>(obj)->setGidiThreshold(t);
}

const char * pt_GidiSetting_getGidiPops(void* obj)
{
    return static_cast<pt::GidiSetting *>(obj)->getGidiPops().c_str();
}

void pt_GidiSetting_setGidiPops(void* obj, const char *s)
{
    static_cast<pt::GidiSetting *>(obj)->setGidiPops(s);
}

const char * pt_GidiSetting_getGidiMap(void* obj)
{
    return static_cast<pt::GidiSetting *>(obj)->getGidiMap().c_str();
}

void pt_GidiSetting_setGidiMap(void* obj, const char *s)
{
    static_cast<pt::GidiSetting *>(obj)->setGidiMap(s);
}

bool pt_GidiSetting_getEnableGidi(void* obj)
{
    return static_cast<pt::GidiSetting *>(obj)->getEnableGidi();
}

void pt_GidiSetting_setEnableGidi(void* obj, bool t)
{
    return static_cast<pt::GidiSetting *>(obj)->setEnableGidi(t);
}


bool pt_GidiSetting_getEnableGidiPowerIteration(void* obj)
{
    return static_cast<pt::GidiSetting *>(obj)->getEnableGidiPowerIteration();
}

void pt_GidiSetting_setEnableGidiPowerIteration(void* obj, bool t)
{
    return static_cast<pt::GidiSetting *>(obj)->setEnableGidiPowerIteration(t);
}

bool pt_GidiSetting_getGammaTransport(void* obj)
{
    return static_cast<pt::GidiSetting *>(obj)->getGammaTransport();
}

void pt_GidiSetting_setGammaTransport(void* obj, bool t)
{
    return static_cast<pt::GidiSetting *>(obj)->setGammaTransport(t);
}