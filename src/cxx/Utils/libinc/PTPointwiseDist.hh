#ifndef Prompt_PointwiseDist_hh
#define Prompt_PointwiseDist_hh

// #include <cstdio>
// #include <utility>
// #include <vector>
#include "PromptCore.hh"
#include "PTRandCanonical.hh"

namespace Prompt {

  // Utility class which provides integration or sampling of a 1D piece-wise
  // linear distribution function. The function is defined by its non-negative
  // values on a given set of points, which must form a proper grid of
  // increasing non-identical values.

  // Copied from NCrystal project v3.1.0

  class PointwiseDist {
  public:
    PointwiseDist( const std::vector<double>& x, const std::vector<double>& y );
    PointwiseDist( std::vector<double>&& x, std::vector<double>&& y );

    //Percentile (argument must be in [0,1]):
    double percentile( double percentile_value ) const { return percentileWithIndex(percentile_value).first; }

    //Sample:
    double sample(SingletonPTRand& rng) const { return percentileWithIndex(rng.generate()).first; }

    const std::vector<double>& getXVals() const { return m_x; }
    const std::vector<double>& getYVals() const { return m_y; }

    //Convenience constructor (would not be needed if we had C++17's std::make_from_tuple):
    PointwiseDist(const std::pair<std::vector<double>,std::vector<double>>& xy ) : PointwiseDist(xy.first,xy.second) {}
    PointwiseDist(std::pair<std::vector<double>,std::vector<double>>&& xy ) : PointwiseDist(std::move(xy.first),std::move(xy.second)) {}

    //versions which also returns index of bin in which returned value resides
    //(i.e returns (value,idx) where value will lie in interval
    //[getXVals().at(idx),getXVals().at(idx+1)]):
    std::pair<double,unsigned> percentileWithIndex( double percentile_value ) const;
    std::pair<double,unsigned> sampleWithIndex( SingletonPTRand& rng ) const { return percentileWithIndex(rng.generate()); }

    //Sample distribution, truncated at some value (throws BadInput exception if
    //xtrunc is less than first x-value in distribution):
    double sampleBelow( SingletonPTRand& rng, double xtrunc ) const;

    //Access CDF (normalised, so last value is 1.0):
    const std::vector<double>& getCDF() const { return m_cdf; }

    //Access the integral from -inf to x (again, of the normalised function, so
    //returns 1.0 if x >= last value, and 0.0 if x <= first value)):
    double commulIntegral( double x ) const;

  private:
    //todo: We have both m_cdf and m_y, although they essentially contain the
    //same info. Could we implement more light-weight version? Could we
    //implement as a non-owning view, i.e. which keeps m_x in span (but likely
    //needs to be possible to be owning still). Or using shared ptrs?
    std::vector<double> m_cdf;
    std::vector<double> m_x;
    std::vector<double> m_y;
  };
}

#endif
