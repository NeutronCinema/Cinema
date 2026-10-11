#include "PTScorer.hh"
#include "PTResourceManager.hh"

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
void pt_ResourceManager_clear();
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

void* pt_ResourceManager_getHist(const char* cfg)
{
    return static_cast<void*>(pt::Singleton<pt::ResourceManager>::getInstance().getHist(cfg));
}

void pt_ResourceManager_clear()
{
   pt::Singleton<pt::ResourceManager>::getInstance().clear();
}
