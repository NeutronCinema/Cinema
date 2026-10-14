#include "PTScorer.hh"
#include "PTResourceManager.hh"
#include "PTParticleProcess.hh"
#include "PTHistBase.hh"
#include "PTPluginRegistry.hh"

#include <exception>
#include <string>

namespace pt = Prompt;

// These wrappers are bound from python by symbol name through ctypes, so
// they keep C linkage and are declared here directly. They used to be
// declared in libinc/PTPythonResource.hh with void returns; that header is no
// longer included because the bridged subset below returns an int status
// instead, and nothing else in the codebase includes it or calls these
// functions from C++.
extern "C" {
void pt_ResourceManager_addNewVolume(unsigned volID);
int pt_ResourceManager_addScorer(unsigned volID, const char* cfg, void* scorer);
int pt_ResourceManager_addSurface(unsigned volID, const char* cfg);
void pt_ResourceManager_cfgVolPhysics(unsigned volID, const char* cfg);
void* pt_ResourceManager_getHist(const char* cfg);
void* pt_HistBase_clone(const void* obj);
void pt_ResourceManager_clear();
// checked variants completing the int-status family below. The hist-module
// merge bridges in PTPythonHist.cc (pt_HistBase_merge/pt_Hist2D_merge) have
// since been converted to the same protocol in place; the unchecked
// pt_makeModelCollection in PTPyCompoundModel.cc remains only as the
// stale-library fallback of compoundModel.py.
int pt_makeModelCollection_checked(const char* cfg, void** out);
int pt_HistBase_merge_checked(void* obj, void* obj2);
int pt_ResourceManager_cfgVolPhysics_checked(unsigned volID, const char* cfg);
int pt_PluginRegistry_load(const char* path);
int pt_PluginRegistry_list(const char** out);
}

// Error protocol of the bridged wrappers (shared with PTPythonLauncher.cc)
// -----------------------------------------------------------------------
// Letting a Prompt::Error exception (a std::runtime_error subclass) escape
// through an extern "C" wrapper into ctypes ends in std::terminate and
// aborts the whole host process with SIGABRT, so a rejected cfg string used
// to be a core dump instead of a catchable error. Bridged wrappers therefore
// catch everything and report failure through their int return value
// (0 = ok, 1 = Prompt::Error::Exception, 2 = other std::exception or unknown)
// while the message goes into the thread-local buffer read back via
// pt_last_error(). The status-plus-pt_last_error protocol was chosen over
// calling PyErr_SetString directly inside the wrappers because it keeps the
// boundary semantics explicit and stays usable from non-python hosts.
extern "C" const char* pt_last_error();
extern "C" int pt_bridge_record_error();

namespace {

// Message of the most recent exception caught at the extern "C" boundary,
// one buffer per thread. Function-local so it is initialised on first use,
// with no static initialisation-order concerns.
std::string &bridgeLastErrorBuf()
{
    static thread_local std::string buf;
    return buf;
}

} // namespace

extern "C" const char* pt_last_error()
{
    return bridgeLastErrorBuf().c_str();
}

// Records the exception currently being handled in the thread-local
// pt_last_error() buffer; only call from a catch(...) block of a bridged
// wrapper. Returns the status code the wrapper passes on to its caller.
extern "C" int pt_bridge_record_error()
{
    try {
        throw;
    }
    catch (const pt::Error::Exception &e) {
        bridgeLastErrorBuf() = e.what();
        return 1;
    }
    catch (const std::exception &e) {
        bridgeLastErrorBuf() = e.what();
        return 2;
    }
    catch (...) {
        bridgeLastErrorBuf() = "unknown non-standard exception crossed the ctypes boundary";
        return 2;
    }
}

void pt_ResourceManager_addNewVolume(unsigned volID)
{
    pt::Singleton<pt::ResourceManager>::getInstance().addNewVolume(volID);
}

// Bridged: a rejected scorer cfg (unknown Scorer= type, unknown ptstate=,
// non-positive bin edges under the log-binning grammar, ...) comes back as a
// nonzero status plus pt_last_error() instead of aborting the host process.
int pt_ResourceManager_addScorer(unsigned volID, const char* cfg, void *scorer)
{
    try {
        auto *s = static_cast<Prompt::Scorer *>(scorer);
        pt::Singleton<pt::ResourceManager>::getInstance().addScorer(volID, cfg, s);
        return 0;
    }
    catch (...) {
        return pt_bridge_record_error();
    }
}

// Bridged: same failure modes as pt_ResourceManager_addScorer (unknown
// surface cfg, unknown volume ID).
int pt_ResourceManager_addSurface(unsigned volID, const char* cfg)
{
    try {
        pt::Singleton<pt::ResourceManager>::getInstance().addSurface(volID, cfg);
        return 0;
    }
    catch (...) {
        return pt_bridge_record_error();
    }
}

void pt_ResourceManager_cfgVolPhysics(unsigned volID, const char* cfg)
{
    pt::Singleton<pt::ResourceManager>::getInstance().cfgVolPhysics(volID, cfg);
}

// Checked sibling of pt_ResourceManager_cfgVolPhysics for the python side to
// migrate to: a rejected material cfg (unknown physics namespace, bad plugin
// cfg key, ...) comes back as a nonzero status plus pt_last_error() instead
// of a Prompt::Error escaping through the extern "C" boundary and aborting
// the host process with SIGABRT. The unchecked variant stays until every
// caller has moved over. (Plugin cfg errors must be testable, and once
// plugins can fail to load, an abort would be unacceptable.)
int pt_ResourceManager_cfgVolPhysics_checked(unsigned volID, const char* cfg)
{
    try {
        pt::Singleton<pt::ResourceManager>::getInstance().cfgVolPhysics(volID, cfg);
        return 0;
    }
    catch (...) {
        return pt_bridge_record_error();
    }
}

// dlopen one physics-model plugin file (checked protocol; 0 = ok). Goes
// through PluginRegistry::loadFile: either the plugin's factories are
// registered or the caller gets a diagnostic naming the file and the
// missing/bad symbol.
int pt_PluginRegistry_load(const char* path)
{
    try {
        pt::Plugin::PluginRegistry::instance().loadFile(path);
        return 0;
    }
    catch (...) {
        return pt_bridge_record_error();
    }
}

// One line per registered factory: "ns\tdescription\n", in a thread-local
// static buffer (fine for the list/selftest CLI use case; not for long-term
// storage). Checked protocol: 0 = ok with *out set, nonzero = failure.
int pt_PluginRegistry_list(const char** out)
{
    try {
        static thread_local std::string buf;
        buf.clear();
        for(auto &pr : pt::Plugin::PluginRegistry::instance().list())
        {
            buf += pr.first;
            buf += '\t';
            buf += pr.second;
            buf += '\n';
        }
        *out = buf.c_str();
        return 0;
    }
    catch (...) {
        return pt_bridge_record_error();
    }
}

void* pt_ResourceManager_getHist(const char* cfg)
{
    return static_cast<void*>(pt::Singleton<pt::ResourceManager>::getInstance().getHist(cfg));
}

// Heap clone of a histogram, for callers that need to own an independent copy
// of a scorer histogram. PromptMPI.gatherHistData writes the MPI-reduced
// content into this clone; writing it into the live scorer histogram instead
// made every later gather (and the re-gather inside save_all_scorers)
// cumulatively inflate the scored data. Dispatches on dimension(): the
// histograms reachable through pt_ResourceManager_getHist are exactly Hist1D
// or Hist2D (scorers own unique_ptr<Hist1D>/<Hist2D>). Returns nullptr when
// the dimension is unknown or the allocation throws; python raises on the
// null result.
void* pt_HistBase_clone(const void* obj)
{
    try {
        auto *hist = static_cast<const pt::HistBase*>(obj);
        switch (hist->dimension()) {
        case 1:
            return new pt::Hist1D(*static_cast<const pt::Hist1D*>(hist));
        case 2:
            return new pt::Hist2D(*static_cast<const pt::Hist2D*>(hist));
        default:
            return nullptr;
        }
    }
    catch (...) {
        return nullptr;
    }
}

void pt_ResourceManager_clear()
{
   pt::Singleton<pt::ResourceManager>::getInstance().clear();
}

// Checked creation of the physics model behind compoundModel.ModelCollection:
// the ParticleProcess constructor evaluates the whole cfg string (unknown
// physics= name, missing or unreadable nccfg file, a material without number
// density, ...) and any rejection used to escape as a C++ exception through
// the ctypes boundary and abort the host process. Same protocol as
// pt_ResourceManager_addScorer: 0 ok, 1 Prompt::Error, 2 other, message via
// pt_last_error(); the new object (never null on status 0) goes through the
// out parameter so the status can carry the failure information.
int pt_makeModelCollection_checked(const char* cfg, void** out)
{
    if (out)
        *out = nullptr;
    if (!cfg || !out) {
        bridgeLastErrorBuf() = "pt_makeModelCollection_checked: null cfg or out pointer";
        return 2;
    }
    try {
        *out = static_cast<void *>(new pt::ParticleProcess(cfg));
        return 0;
    }
    catch (...) {
        return pt_bridge_record_error();
    }
}

// Checked merge for the histogram-module merge() entry points. HistBase::merge
// throws on mismatched xmin/xmax/nbins and Hist2D::merge (the override reached
// here through virtual dispatch) adds its own binning checks plus a reference
// dynamic_cast that throws std::bad_cast on a cross-type argument; all of that
// must surface as a nonzero status instead of an abort. The call goes through
// a HistBase* so the virtual merge of the actual derived class runs (this is
// what keeps the histogram-core Est1D::merge override effective for callers of
// this bridge).
int pt_HistBase_merge_checked(void* obj, void* obj2)
{
    try {
        static_cast<pt::HistBase *>(obj)->merge(*static_cast<pt::HistBase *>(obj2));
        return 0;
    }
    catch (...) {
        return pt_bridge_record_error();
    }
}
