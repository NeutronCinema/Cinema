#ifndef Prompt_Vector_hh
#define Prompt_Vector_hh

////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    //
//                                                                            //
//  Copyright 2021-2026 Cinema developers                                     //
//                                                                            //
//  Licensed under the Apache License, Version 2.0 (the "License");           //
//  you may not use this file except in compliance with the License.          //
//  You may obtain a copy of the License at                                   //
//                                                                            //
//      http://www.apache.org/licenses/LICENSE-2.0                            //
//                                                                            //
//  Unless required by applicable law or agreed to in writing, software       //
//  distributed under the License is distributed on an "AS IS" BASIS,         //
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  //
//  See the License for the specific language governing permissions and       //
//  limitations under the License.                                            //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

#include <ostream>
#include <cmath>
#include "PTException.hh"
//Simple Vector class

namespace Prompt {

  class Vector
  {
  public:

    Vector(double x, double y, double z);
    Vector(const Vector&);
    Vector();//default constructs null vector
    ~Vector(){}

    Vector& operator=( const Vector&);
    Vector operator*(const Vector&) const;
    Vector operator* (double ) const;
    Vector operator/ (double ) const;
    Vector& operator*= (double );
    Vector& operator+= (const Vector&);
    Vector& operator-= (const Vector&);
    Vector& operator/= (double );

    Vector operator-() const;
    Vector operator+( const Vector&) const;
    Vector operator-( const Vector&) const;

    friend std::ostream& operator << (std::ostream &, const Vector&);

    bool operator==( const Vector&) const;
    bool operator!=( const Vector&) const;

    void print() const;
    Vector unit() const;//slow
    void normalise();//better
    Vector cross(const Vector&) const;
    void cross_inplace(const Vector&);
    double dot(const Vector&) const;
    double angleCos(const Vector&) const;//better
    double angle(const Vector&) const;//slow
    double angle_highres(const Vector&) const;//very slow, but precise even for small angles
    double mag() const;//slow
    void magdir(double &mag, Vector &dir) const; //slow
    double mag2() const;//better
    void set(double x, double y, double z);
    void setMag(double );//slow
    bool isParallel(const Vector&, double epsilon = 1e-10) const;
    bool isOrthogonal(const Vector&, double epsilon = 1e-10) const;
    bool isUnitVector(double tolerance = 1e-10) const;
    bool isStrictNullVector() const { return m_x==0 && m_y==0 && m_z==0; }
    
    void findRotationMatrixFrom001(double rotation_matrix[9]) const;
    Vector applyRotationMatrix(const double rotation_matrix[9]) const;

    inline const double& x() const { return m_x; }
    inline const double& y() const { return m_y; }
    inline const double& z() const { return m_z; }
    inline double& x() { return m_x; }
    inline double& y() { return m_y; }
    inline double& z() { return m_z; }

    bool operator <(const Vector &o) const {
      return ( m_x != o.m_x ? m_x < o.m_x :
               ( m_y != o.m_y ? m_y < o.m_y : m_z < o.m_z ) );
    }
  protected:
    //Keep data members exactly like this, so Vector objects can reliably be
    //reinterpreted as double[3] arrays and vice versa:
    double m_x;
    double m_y;
    double m_z;
  };

  //For interpreting double[3] arrays as Vector:
  static inline Vector& asVect( double (&v)[3] ) { return *reinterpret_cast<Vector*>(&v); }
  static inline const Vector& asVect( const double (&v)[3] ) { return *reinterpret_cast<const Vector*>(&v); }

  std::ostream& operator << (std::ostream &, const Vector&);

}

#ifndef PT_VECTOR_CAST
#  define PT_VECTOR_CAST(v) (reinterpret_cast<double(&)[3]>(v))
#  define PT_CVECTOR_CAST(v) (reinterpret_cast<const double(&)[3]>(v))
#endif


////////////////////////////
// Inline implementations //
////////////////////////////

void inline Prompt::Vector::findRotationMatrixFrom001(double rotation_matrix[9]) const {
    Vector vec_rotated_from_001_unit = this->unit();

    if (vec_rotated_from_001_unit == Vector(0, 0, 1)) {
        // Identity matrix for no rotation
        for (int i = 0; i < 9; ++i) {
            rotation_matrix[i] = (i % 4 == 0) ? 1.0 : 0.0;
        }
        return;
    }

    // Simplified cross product for z-axis [0, 0, 1] and vec_rotated_from_001_unit
    Vector v(-vec_rotated_from_001_unit.y(), vec_rotated_from_001_unit.x(), 0);
    double s = v.mag();
    double c = vec_rotated_from_001_unit.z(); // Simplified dot product with z-axis

    if (s == 0.0) {
      // Degenerate case: the target vector is exactly along the z-axis
      // (x == y == 0), for which the Rodrigues construction below would divide
      // by s*s == 0 and produce an all-NaN matrix. The exact +z direction is
      // handled above, so this is either +z up to rounding of the
      // normalisation (use the identity), or the antiparallel (0,0,-1)
      // direction, for which the rotation is not unique: use the 180-degree
      // rotation about the x-axis, which maps +z onto -z.
      if (vec_rotated_from_001_unit.z() > 0.0) {
        for (int i = 0; i < 9; ++i) {
          rotation_matrix[i] = (i % 4 == 0) ? 1.0 : 0.0;
        }
      } else {
        rotation_matrix[0] = 1.0;
        rotation_matrix[1] = 0.0;
        rotation_matrix[2] = 0.0;
        rotation_matrix[3] = 0.0;
        rotation_matrix[4] = -1.0;
        rotation_matrix[5] = 0.0;
        rotation_matrix[6] = 0.0;
        rotation_matrix[7] = 0.0;
        rotation_matrix[8] = -1.0;
      }
      return;
    }

    // Skew-symmetric matrix in 1D array
    double k_mat[9] = {
        0, -v.z(), v.y(),
        v.z(), 0, -v.x(),
        -v.y(), v.x(), 0
    };

    // Rodrigues' rotation formula
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            rotation_matrix[i * 3 + j] = (i == j) + k_mat[i * 3 + j] + 
                (k_mat[i * 3 + 0] * k_mat[0 * 3 + j] + 
                 k_mat[i * 3 + 1] * k_mat[1 * 3 + j] + 
                 k_mat[i * 3 + 2] * k_mat[2 * 3 + j]) * ((1 - c) / (s * s));
        }
    }
}

Prompt::Vector inline Prompt::Vector::applyRotationMatrix(const double rotation_matrix[9]) const {
    return Vector(
        rotation_matrix[0] * m_x + rotation_matrix[1] * m_y + rotation_matrix[2] * m_z,
        rotation_matrix[3] * m_x + rotation_matrix[4] * m_y + rotation_matrix[5] * m_z,
        rotation_matrix[6] * m_x + rotation_matrix[7] * m_y + rotation_matrix[8] * m_z
    );
}


inline Prompt::Vector::Vector()
  : m_x(0.), m_y(0.), m_z(0.)
{
}

inline Prompt::Vector::Vector(double vx, double vy, double vz)
  : m_x(vx), m_y(vy), m_z(vz)
{
}

inline Prompt::Vector::Vector(const Prompt::Vector& v)
  : m_x(v.m_x), m_y(v.m_y), m_z(v.m_z)
{
}

inline void Prompt::Vector::set(double xx, double yy, double zz)
{
  m_x = xx;
  m_y = yy;
  m_z = zz;
}

inline double Prompt::Vector::mag() const
{
  return std::sqrt( m_x*m_x + m_y*m_y + m_z*m_z );
}

inline void Prompt::Vector::magdir(double &mag, Vector &dir) const
{
  double themag2 = mag2();
  if (themag2==1.0)
  {
    mag=1.;
    dir.set(m_x, m_y, m_z);
    return;
  }
  if (!themag2)
    PROMPT_THROW(CalcError,"PTVector::magdir(): Can't scale null-vector.");
  mag = std::sqrt(themag2);
  double f = 1./mag;
  dir.set(m_x*f, m_y*f, m_z*f);
}

inline double Prompt::Vector::mag2() const
{
  return m_x*m_x + m_y*m_y + m_z*m_z;
}

inline double Prompt::Vector::dot(const Prompt::Vector& o) const
{
  return m_x*o.m_x + m_y*o.m_y + m_z*o.m_z;
}

inline Prompt::Vector& Prompt::Vector::operator=( const Prompt::Vector& o)
{
  m_x = o.m_x;
  m_y = o.m_y;
  m_z = o.m_z;
  return *this;
}

inline Prompt::Vector& Prompt::Vector::operator+=( const Prompt::Vector& o)
{
  m_x += o.m_x;
  m_y += o.m_y;
  m_z += o.m_z;
  return *this;
}

inline Prompt::Vector& Prompt::Vector::operator-=( const Prompt::Vector& o)
{
  m_x -= o.m_x;
  m_y -= o.m_y;
  m_z -= o.m_z;
  return *this;
}

inline Prompt::Vector& Prompt::Vector::operator*= (double f)
{
  m_x *= f;
  m_y *= f;
  m_z *= f;
  return *this;
}

inline Prompt::Vector& Prompt::Vector::operator/= (double f)
{
  double ff(1.0/f);
  m_x *= ff;
  m_y *= ff;
  m_z *= ff;
  return *this;
}

inline bool Prompt::Vector::operator==( const Prompt::Vector& o) const
{
  return ( m_x==o.m_x && m_y==o.m_y && m_z==o.m_z );
}

inline bool Prompt::Vector::operator!=( const Prompt::Vector& o) const
{
  return !( (*this) == o );
}

inline Prompt::Vector Prompt::Vector::operator/ (double f) const
{
  return Vector( m_x/f, m_y/f, m_z/f );
}

inline Prompt::Vector Prompt::Vector::operator* (double f) const
{
  return Vector( m_x*f, m_y*f, m_z*f );
}

inline Prompt::Vector Prompt::Vector::operator*(const Prompt::Vector& o) const
{
  return Vector( m_y*o.m_z - m_z*o.m_y,
                 m_z*o.m_x - m_x*o.m_z,
                 m_x*o.m_y - m_y*o.m_x );
}

inline void Prompt::Vector::cross_inplace(const Vector&o)
{
  double xx = m_y*o.m_z - m_z*o.m_y;
  double yy = m_z*o.m_x - m_x*o.m_z;
  m_z = m_x*o.m_y - m_y*o.m_x;
  m_x = xx;
  m_y = yy;
}

inline Prompt::Vector Prompt::Vector::operator-() const
{
  return Prompt::Vector( -m_x, -m_y, -m_z );
}

inline Prompt::Vector Prompt::Vector::operator+( const Prompt::Vector& o ) const
{
  return Prompt::Vector( m_x+o.m_x, m_y+o.m_y, m_z+o.m_z );
}

inline Prompt::Vector Prompt::Vector::operator-( const Prompt::Vector& o ) const
{
  return Prompt::Vector( m_x-o.m_x, m_y-o.m_y, m_z-o.m_z );
}

inline Prompt::Vector Prompt::Vector::unit() const
{
  double themag2 = mag2();
  if (themag2==1.0)
    return *this;
  if (!themag2)
    PROMPT_THROW(CalcError,"PTVector::unit(): Can't scale null-vector.");
  double factor = 1.0/std::sqrt(themag2);
  return Prompt::Vector(m_x*factor, m_y*factor, m_z*factor);
}

inline void Prompt::Vector::normalise()
{
  double themag2 = mag2();
  if (themag2==1.0)
    return;
  if (!themag2)
    PROMPT_THROW(CalcError,"PTVector::normalise(): Can't scale null-vector.");
  double f = 1.0/std::sqrt(themag2);
  m_x *= f;
  m_y *= f;
  m_z *= f;
}

inline Prompt::Vector Prompt::Vector::cross(const Prompt::Vector& o) const
{
  return *this * o;
}

inline bool Prompt::Vector::isParallel(const Prompt::Vector& vec2, double epsilon) const
{
  //NB: using '>' rather than '>=' to have null-vectors never be parallel to
  //anything (including themselves, which we could of course check against).
  double dp = dot(vec2);
  return dp*dp > mag2() * vec2.mag2() * ( 1.0 - epsilon);
}

inline bool Prompt::Vector::isOrthogonal(const Vector& vec2, double epsilon) const
{
  //NB: using '<' rather than '<=' to have null-vectors never be orthogonal to
  //anything.
  double dp = dot(vec2);
  return dp*dp < mag2() * vec2.mag2() * epsilon;
}

inline double Prompt::Vector::angle(const Prompt::Vector& vec2) const
{
  double norm = std::sqrt( mag2()*vec2.mag2() );
  if (!norm)
    PROMPT_THROW(CalcError,"PTVector::angle(): Can't find angle to/from null-vector.");
  double result = dot(vec2) / norm;
  return std::acos( std::min(1.,std::max(-1.,result)) );
}

inline double Prompt::Vector::angleCos(const Prompt::Vector& vec2) const
{
  double norm = std::sqrt( mag2()*vec2.mag2() );
  if (!norm)
    PROMPT_THROW(CalcError,"PTVector::angle(): Can't find angle to/from null-vector.");
  double result = dot(vec2) / norm;
  return std::min(1.,std::max(-1.,result)) ;
}


inline double Prompt::Vector::angle_highres(const Prompt::Vector& vec2) const
{
  //Based on formula on page 47 of
  //https://people.eecs.berkeley.edu/~wkahan/Mindless.pdf "How Futile are
  //Mindless Assessments of Roundoff in Floating-Point Computation?" by W. Kahan
  //(Jan 11, 2006):

  Prompt::Vector a(*this);
  Prompt::Vector b(vec2);
  double mag2_a = a.mag2();
  double mag2_b = b.mag2();
  if (!mag2_a||!mag2_b)
    PROMPT_THROW(CalcError,"PTVector::angle_highres(): Can't find angle to/from null-vector.");
  a *= 1.0/std::sqrt(mag2_a);
  b *= 1.0/std::sqrt(mag2_b);
  return 2*std::atan2((a-b).mag(),(a+b).mag());
}

inline bool Prompt::Vector::isUnitVector(double tolerance) const
{
  return std::abs( mag2() - 1.0 ) < tolerance;
}


#endif
