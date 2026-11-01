#include "PTPointwiseDist.hh"
#include <algorithm>
#include <iterator>
#include "PTMath.hh"

namespace PT = Prompt;

PT::PointwiseDist::PointwiseDist(const std::vector<double> &xvals, const std::vector<double> &yvals)
  : PointwiseDist( std::vector<double>(xvals), std::vector<double>(yvals) )
{
}

PT::PointwiseDist::PointwiseDist( std::vector<double>&& xvals, std::vector<double>&& yvals )
  : m_x(xvals), m_y(yvals)
{
  if(m_x.size()!=m_y.size() || m_y.size()<2 )
    PROMPT_THROW(CalcError, "input vector size error.");

  if(!std::is_sorted(m_x.begin(),m_x.end()))
    PROMPT_THROW(CalcError, "points of the distribution are not sorted.");

  for(std::size_t i=0;i<m_y.size();i++)
  {
    if(m_y[i]<0.)
      PROMPT_THROW(CalcError, "function is negative.");

    if(std::isinf(m_y[i]))
      PROMPT_THROW(CalcError, "function is not finite.");
  }

  m_cdf.reserve(m_y.size());
  StableSum totalArea;

  m_cdf.push_back(0.);
  for(std::size_t i=1;i<m_y.size();i++)
  {
    double area = (m_x[i]-m_x[i-1])*0.5*(m_y[i]+m_y[i-1]);
    if(area<0)
      PROMPT_THROW(CalcError, "Negative probability density");
    totalArea.add( area );
    m_cdf.push_back( totalArea.sum() );
  }

  double totalAreaVal = totalArea.sum();
  if ( !(totalAreaVal>0.0) )
    PROMPT_THROW(CalcError, "No area in distribution.");

  double normfact = 1.0/totalAreaVal;
  for ( auto& e : m_cdf )
    e *= normfact;
  for ( auto& e : m_y )
    e *= normfact;
  pt_assert( std::abs(1.0-m_cdf.back()) < 1.0e-14 );
  m_cdf.back() = 1.0;
}

std::pair<double,unsigned> PT::PointwiseDist::percentileWithIndex(double p ) const
{
  pt_assert(p>=0.&&p<=1.0);
  if(p==1.)
    return std::pair<double,unsigned>(m_x.back(), m_x.size()-2);

  std::size_t i = std::max<std::size_t>(std::min<std::size_t>(std::lower_bound(m_cdf.begin(), m_cdf.end(), p)-m_cdf.begin(),m_cdf.size()-1),1);
  pt_assert( i>0 && i < m_x.size() );
  double dx = m_x[i]-m_x[i-1];
  double c = (p-m_cdf[i-1]);
  double a = m_y[i-1];
  double d = m_y[i] - a;
  double zdx;
  if (!a) {
    zdx = d>0.0 ? std::sqrt( ( 2.0 * c * dx ) / d ) : 0.5*dx;//a=0 and d=0 should not really happen...
  } else {
    double e = d * c / ( dx * a * a );
    if (std::abs(e)>1e-7) {
      //apply formula:
      zdx = ( std::sqrt( 1.0 + 2.0 * e ) - 1.0 ) * dx * a / d;
    } else {
      //calculate via expansion (solves numerical issue when d is near zero):
      zdx = ( 1 + 0.5 * e * ( e - 1.0 ) ) * c / a;
    }
  }
  return std::pair<double,unsigned>( ptclamp(m_x[i-1] + zdx,m_x[i-1],m_x[i]), i-1 );
}

double PT::PointwiseDist::commulIntegral( double x ) const
{
  //Above or below edges is easy:
  if ( x <= m_x.front() )
    return 0.0;
  if ( x >= m_x.back() )
    return 1.0;

  //Find bin with binary search:
  auto it = std::upper_bound( m_x.begin(), m_x.end(), x );
  pt_assert( it != m_x.end() );
  pt_assert( it != m_x.begin() );

  //We are in the interval [std::prev(it),it], find parameters of this last bin:
  auto i1 = std::distance(m_x.begin(),it);
  pt_assert(i1>0);
  auto i0 = i1 - 1;
  const double x1 = m_x[i0];
  const double y1 = m_y[i0];
  const double x2 = m_x[i1];
  const double y2 = m_y[i1];

  //Find contribution in this bin as as
  //<length in bin>*<average height in bin over used part>:
  pt_assert( x2 - x1 > 0.0 );
  const double dx = x-x1;
  const double slope = ( y2-y1 ) / (x2-x1);
  const double last_bin_contrib = dx * ( y1 + 0.5 * dx * slope );

  //Combine with preceding bins from m_cdf:
  return m_cdf[i0] + last_bin_contrib;
}

double PT::PointwiseDist::sampleBelow( SingletonPTRand& rng, double xtrunc ) const
{
  //Above or below edges is easy:
  if ( xtrunc <= m_x.front() ) {
    if ( xtrunc == m_x.front() )
      return m_x.front();
    PROMPT_THROW2(BadInput,"PointwiseDist::sampleBelow asked to sample point below distribution");
  }
  if ( xtrunc >= m_x.back() )
    return sample(rng);

  return percentile( rng.generate() * commulIntegral( xtrunc ) );

}
