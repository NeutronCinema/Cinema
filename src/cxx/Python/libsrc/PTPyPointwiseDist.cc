
#include "PTPython.hh"
#include "PTPointwiseDist.hh"
#include <vector>

void* pt_PointwiseDist_new(const double* x, const double* y, size_t n)
{
  std::vector<double> xv(x, x + n);
  std::vector<double> yv(y, y + n);
  return new Prompt::PointwiseDist(std::move(xv), std::move(yv));
}

void pt_PointwiseDist_delete(void* obj)
{
  delete static_cast<Prompt::PointwiseDist*>(obj);
}

double pt_PointwiseDist_percentile(void* obj, double p)
{
  auto* pwd = static_cast<Prompt::PointwiseDist*>(obj);
  return pwd->percentile(p);
}

void pt_PointwiseDist_percentile_many(void* obj, double* in, double* out, size_t n)
{
  auto* pwd = static_cast<Prompt::PointwiseDist*>(obj);
  for (size_t i = 0; i < n; ++i) {
    out[i] = pwd->percentile(in[i]);
  }
}