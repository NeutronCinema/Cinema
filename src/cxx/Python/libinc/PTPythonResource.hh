#ifndef Prompt_PythonResource_hh
#define Prompt_PythonResource_hh

#include "PTScorer.hh"

#ifdef __cplusplus
extern "C" {
#endif
 
void pt_ResourceManager_addNewVolume(unsigned volID);
// addScorer/addSurface bridge C++ rejections to python: return 0 on success,
// nonzero after recording the message retrievable via pt_last_error().
int pt_ResourceManager_addScorer(unsigned volID, const char* cfg, void* scorer);
int pt_ResourceManager_addSurface(unsigned volID, const char* cfg);
void pt_ResourceManager_cfgVolPhysics(unsigned volID, const char* cfg);
void* pt_ResourceManager_getHist(const char* cfg);
void pt_ResourceManager_clear();

#ifdef __cplusplus
}
#endif

#endif
