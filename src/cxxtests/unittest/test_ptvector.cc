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

#include "../doctest.h"
#include <cmath>
#include <random>

#include "PTVector.hh"

namespace pt = Prompt;

namespace {

//Check that R = findRotationMatrixFrom001(v) is a proper rotation (R^T R = I,
//det(R) = +1) which maps the +z axis onto unit(v).
void checkRotationOnto(const pt::Vector& v)
{
  double R[9];
  v.findRotationMatrixFrom001(R);

  //Orthonormality, R^T R == I:
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) {
      double rtr = 0.0;
      for (int k = 0; k < 3; ++k)
        rtr += R[k * 3 + i] * R[k * 3 + j];
      CHECK( std::fabs(rtr - (i == j ? 1.0 : 0.0)) < 1e-12 );
    }

  //det(R) == +1, i.e. a rotation and not a reflection:
  double det = R[0] * (R[4] * R[8] - R[5] * R[7])
             - R[1] * (R[3] * R[8] - R[5] * R[6])
             + R[2] * (R[3] * R[7] - R[4] * R[6]);
  CHECK( std::fabs(det - 1.0) < 1e-12 );

  //R applied to (0,0,1) reproduces unit(v) componentwise:
  pt::Vector img = pt::Vector(0, 0, 1).applyRotationMatrix(R);
  pt::Vector u = v.unit();
  CHECK( std::fabs(img.x() - u.x()) < 1e-12 );
  CHECK( std::fabs(img.y() - u.y()) < 1e-12 );
  CHECK( std::fabs(img.z() - u.z()) < 1e-12 );
  CHECK( std::fabs(img.mag() - 1.0) < 1e-12 );
}

} // namespace

TEST_CASE("Vector.mag2/mag follow Pythagoras")
{
  CHECK( pt::Vector(3, 4, 0).mag2() == 25.0 );
  CHECK( pt::Vector(3, 4, 0).mag() == 5.0 );
  CHECK( pt::Vector(1, 2, 2).mag2() == 9.0 );
  CHECK( pt::Vector(1, 2, 2).mag() == 3.0 );
  CHECK( pt::Vector(1, 1, 1).mag2() == 3.0 );
  CHECK( pt::Vector(1, 1, 1).mag() == doctest::Approx(std::sqrt(3.0)).epsilon(1e-12) );
  //Consistency between the two magnitudes and the scalar product:
  pt::Vector v(0.5, -1.25, 3.0);
  CHECK( v.mag2() == doctest::Approx(v.dot(v)).epsilon(1e-12) );
  CHECK( v.mag() == doctest::Approx(std::sqrt(v.mag2())).epsilon(1e-12) );
}

TEST_CASE("Vector.unit and normalise produce unit-length vectors and agree")
{
  pt::Vector v(3, 4, 0);
  pt::Vector u = v.unit();
  CHECK( u.mag() == doctest::Approx(1.0).epsilon(1e-12) );
  pt::Vector w = v;
  w.normalise();
  //unit() and normalise() go through the identical arithmetic (reciprocal of
  //the square root of mag2()), so the results are bitwise identical:
  CHECK( w == u );

  //Already unit-length input takes the exact shortcut in both functions:
  pt::Vector a(1, 0, 0);
  CHECK( a.unit() == a );
  pt::Vector b(0, 1, 0);
  b.normalise();
  CHECK( b == pt::Vector(0, 1, 0) );
  CHECK( b.isUnitVector() );
}

TEST_CASE("Vector.unit, normalise and magdir reject null vectors")
{
  pt::Vector v0;
  CHECK( v0.isStrictNullVector() );
  REQUIRE_THROWS_AS( v0.unit(), pt::Error::CalcError );
  REQUIRE_THROWS_AS( v0.normalise(), pt::Error::CalcError );
  double mag;
  pt::Vector dir;
  REQUIRE_THROWS_AS( v0.magdir(mag, dir), pt::Error::CalcError );
}

TEST_CASE("Vector.magdir shortcut for unit-length input is exact")
{
  //mag2()==1.0 exactly takes the shortcut path returning mag=1 and dir=copy:
  pt::Vector v(1, 0, 0);
  double mag;
  pt::Vector dir;
  v.magdir(mag, dir);
  CHECK( mag == 1.0 );
  CHECK( dir == v );

  //Generic input: mag is the euclidean length, dir is the unit vector (same
  //reciprocal-sqrt arithmetic as unit(), so bitwise identical):
  pt::Vector w(0, 0, 3);
  w.magdir(mag, dir);
  CHECK( mag == 3.0 );
  CHECK( dir.z() == 1.0 );
  pt::Vector u(1, 2, 2);
  u.magdir(mag, dir);
  CHECK( mag == 3.0 );
  CHECK( dir == pt::Vector(1, 2, 2).unit() );
}

TEST_CASE("Vector dot and cross satisfy the standard algebraic identities")
{
  pt::Vector a(1, 2, 3);
  pt::Vector b(4, 5, 6);

  //Dot product is commutative:
  CHECK( a.dot(b) == b.dot(a) );
  CHECK( a.dot(b) == 32.0 );

  //Cross product is anticommutative and orthogonal to both inputs:
  pt::Vector c = a.cross(b);
  CHECK( c == pt::Vector(-3, 6, -3) );
  CHECK( c == -(b.cross(a)) );
  CHECK( c.dot(a) == 0.0 );
  CHECK( c.dot(b) == 0.0 );

  //Lagrange identity: |a x b|^2 + (a.b)^2 == |a|^2 |b|^2:
  CHECK( c.mag2() + a.dot(b) * a.dot(b)
         == doctest::Approx(a.mag2() * b.mag2()).epsilon(1e-12) );
}

TEST_CASE("Vector operator* between two vectors is the cross product")
{
  //operator*(Vector) is *not* a componentwise product but the cross product -
  //pin that somewhat surprising semantics:
  pt::Vector xhat(1, 0, 0), yhat(0, 1, 0), zhat(0, 0, 1);
  CHECK( xhat * yhat == zhat );
  CHECK( yhat * zhat == xhat );
  CHECK( zhat * xhat == yhat );
  CHECK( yhat * xhat == -zhat );

  pt::Vector a(1, 2, 3), b(-0.5, 2.0, 7.25);
  CHECK( a * b == a.cross(b) );
  CHECK( b * a == a.cross(b) * -1.0 );
}

TEST_CASE("Vector cross_inplace matches cross")
{
  pt::Vector a(1, 2, 3), b(4, 5, 6);
  pt::Vector expected = a.cross(b);

  pt::Vector w = a;
  w.cross_inplace(b);
  //The z component is computed before x,y are overwritten, so the in-place
  //variant must give bitwise the same result as the out-of-place one:
  CHECK( w == expected );
  CHECK( w.z() == -3.0 );

  //Self cross product is the null vector, also in place:
  pt::Vector s(1, 2, 3);
  s.cross_inplace(s);
  CHECK( s.isStrictNullVector() );
}

TEST_CASE("Vector.angle knows right, straight and zero angles and matches angle_highres")
{
  pt::Vector xhat(1, 0, 0), zhat(0, 0, 1);
  CHECK( std::fabs(xhat.angle(zhat) - M_PI / 2) < 1e-15 );
  pt::Vector p(3, 4, 0);
  CHECK( p.angle(p) == 0.0 );
  CHECK( std::fabs(xhat.angle(pt::Vector(-5, 0, 0)) - M_PI) < 1e-15 );

  //angle() (acos based) and angle_highres() (Kahan atan2 based) agree on
  //fixed non-degenerate vector pairs:
  const pt::Vector pairs[] = {
      pt::Vector(1, 2, 3),    pt::Vector(3, 2, 1),
      pt::Vector(1, 0, 0),    pt::Vector(1, 1, 0),
      pt::Vector(2, -1, 0.5), pt::Vector(-1, 3, 2),
  };
  for (unsigned i = 0; i < sizeof(pairs) / sizeof(pairs[0]); i += 2) {
    CHECK( std::fabs(pairs[i].angle(pairs[i + 1])
                     - pairs[i].angle_highres(pairs[i + 1])) < 1e-12 );
  }

  //Null vectors are rejected:
  pt::Vector v0;
  REQUIRE_THROWS_AS( xhat.angle(v0), pt::Error::CalcError );
  REQUIRE_THROWS_AS( xhat.angle_highres(v0), pt::Error::CalcError );
  REQUIRE_THROWS_AS( xhat.angleCos(v0), pt::Error::CalcError );
}

TEST_CASE("Vector.angle_highres resolves tiny angles that angle() rounds to zero")
{
  //A 1e-8 rad rotation of the x-axis towards y: cos(1e-8) rounds to exactly
  //1.0 in double precision, so the acos based angle() yields exactly zero,
  //while the Kahan formula keeps full precision:
  pt::Vector a(1, 0, 0);
  pt::Vector b(std::cos(1e-8), std::sin(1e-8), 0.0);
  CHECK( a.angle(b) == 0.0 );
  double hr = a.angle_highres(b);
  CHECK( hr > 0.0 );
  CHECK( std::fabs(hr - 1e-8) < 1e-15 );
}

TEST_CASE("Vector.angleCos stays within [-1,1] for unnormalized inputs")
{
  //Unnormalized parallel and antiparallel inputs clamp onto the exact poles:
  CHECK( pt::Vector(1, 0, 0).angleCos(pt::Vector(2, 0, 0)) == 1.0 );
  CHECK( pt::Vector(1, 0, 0).angleCos(pt::Vector(-2, 0, 0)) == -1.0 );
  CHECK( pt::Vector(3, 4, 0).angleCos(pt::Vector(0, 0, 5)) == 0.0 );

  //Deterministic pseudo-random sweep: the result must always be a valid
  //cosine, whatever rounding the dot/norm division produces:
  std::mt19937 rng(113u);
  std::uniform_real_distribution<double> uni(-10.0, 10.0);
  for (int i = 0; i < 200; ++i) {
    pt::Vector a(uni(rng), uni(rng), uni(rng));
    pt::Vector b(uni(rng), uni(rng), uni(rng));
    double c = a.angleCos(b);
    CHECK_MESSAGE( c >= -1.0, "angleCos below -1" );
    CHECK_MESSAGE( c <= 1.0, "angleCos above 1" );
  }
}

TEST_CASE("Vector.isParallel and isOrthogonal exclude null vectors; isUnitVector tolerance")
{
  pt::Vector v0;
  pt::Vector xhat(1, 0, 0), yhat(0, 1, 0);

  //Documented NB: null vectors are never parallel or orthogonal to anything,
  //not even to themselves:
  CHECK_FALSE( v0.isParallel(v0) );
  CHECK_FALSE( v0.isParallel(xhat) );
  CHECK_FALSE( xhat.isParallel(v0) );
  CHECK_FALSE( v0.isOrthogonal(v0) );
  CHECK_FALSE( v0.isOrthogonal(xhat) );
  CHECK_FALSE( xhat.isOrthogonal(v0) );

  CHECK( xhat.isParallel(pt::Vector(2, 0, 0)) );
  CHECK_FALSE( xhat.isParallel(yhat) );
  CHECK( xhat.isOrthogonal(yhat) );
  CHECK_FALSE( xhat.isOrthogonal(pt::Vector(1, 1, 0)) );

  //isUnitVector compares |mag2|-1 against the tolerance:
  CHECK( xhat.isUnitVector() );
  CHECK( pt::Vector(1.0 + 1e-11, 0, 0).isUnitVector() );
  CHECK_FALSE( pt::Vector(2, 0, 0).isUnitVector() );
  CHECK_FALSE( pt::Vector(1.0 + 1e-5, 0, 0).isUnitVector() );
  CHECK( pt::Vector(2, 0, 0).isUnitVector(5.0) );
}

TEST_CASE("Vector operator< is a lexicographic ordering")
{
  pt::Vector a(1, 2, 3);
  CHECK( a < pt::Vector(1, 2, 4) );
  CHECK_FALSE( pt::Vector(1, 2, 4) < a );
  CHECK_FALSE( pt::Vector(2, 0, 0) < pt::Vector(1, 9, 9) );
  CHECK( pt::Vector(0, 0, -1) < pt::Vector(0, 0, 1) );
  //Strict ordering never holds an element against itself:
  CHECK_FALSE( a < a );
  //x dominates y dominates z, i.e. usable as a strict weak order for maps:
  CHECK( pt::Vector(0, 9, 9) < pt::Vector(1, 0, 0) );
  CHECK( pt::Vector(1, 0, 9) < a );
}

TEST_CASE("Vector asVect reinterpretation round-trips double[3]")
{
  //The header guarantees Vector to have the exact memory layout of double[3],
  //so the reinterpretations below must round-trip both ways:
  double arr[3] = { 1.0, 2.0, 3.0 };
  pt::Vector& v = pt::asVect(arr);
  CHECK( v.x() == 1.0 );
  CHECK( v.y() == 2.0 );
  CHECK( v.z() == 3.0 );

  v.set(4.0, 5.0, 6.0);
  CHECK( arr[0] == 4.0 );
  CHECK( arr[1] == 5.0 );
  CHECK( arr[2] == 6.0 );

  arr[1] = 7.0;
  CHECK( v.y() == 7.0 );

  pt::Vector w(9.0, 8.0, 7.0);
  double(&warr)[3] = PT_VECTOR_CAST(w);
  CHECK( warr[0] == 9.0 );
  CHECK( warr[1] == 8.0 );
  CHECK( warr[2] == 7.0 );
}

TEST_CASE("findRotationMatrixFrom001 maps +z onto unit(v), including the antiparallel pole")
{
  //Directions spanning all octants, axis directions, scaled z directions and
  //both poles. The (0,0,-1) pole used to yield an all-NaN matrix (division by
  //s*s==0 in the Rodrigues formula); it is now the exact 180-degree rotation
  //about the x-axis:
  const pt::Vector dirs[] = {
      pt::Vector(0, 0, 1),    pt::Vector(0, 0, -1),
      pt::Vector(1, 0, 0),    pt::Vector(-1, 0, 0),
      pt::Vector(0, 1, 0),    pt::Vector(0, -1, 0),
      pt::Vector(1, 2, 3),    pt::Vector(-1, 2, 3),
      pt::Vector(1, -2, 3),   pt::Vector(-1, -2, -3),
      pt::Vector(0.3, 0.4, 0), pt::Vector(-2, 0.3, -0.1),
      pt::Vector(1e-8, 1e-8, -1.0), pt::Vector(0, 0, 3), pt::Vector(0, 0, -3),
  };
  for (const auto& v : dirs)
    checkRotationOnto(v);

  //The +z pole is the exact identity matrix:
  double R[9];
  pt::Vector(0, 0, 1).findRotationMatrixFrom001(R);
  CHECK( R[0] == 1.0 );
  CHECK( R[1] == 0.0 );
  CHECK( R[2] == 0.0 );
  CHECK( R[3] == 0.0 );
  CHECK( R[4] == 1.0 );
  CHECK( R[5] == 0.0 );
  CHECK( R[6] == 0.0 );
  CHECK( R[7] == 0.0 );
  CHECK( R[8] == 1.0 );

  //The -z pole is the exact 180-degree rotation about the x-axis, mapping
  //+z onto -z and leaving x unchanged:
  pt::Vector(0, 0, -1).findRotationMatrixFrom001(R);
  CHECK( R[0] == 1.0 );
  CHECK( R[1] == 0.0 );
  CHECK( R[2] == 0.0 );
  CHECK( R[3] == 0.0 );
  CHECK( R[4] == -1.0 );
  CHECK( R[5] == 0.0 );
  CHECK( R[6] == 0.0 );
  CHECK( R[7] == 0.0 );
  CHECK( R[8] == -1.0 );
  pt::Vector img = pt::Vector(0, 0, 1).applyRotationMatrix(R);
  CHECK( img == pt::Vector(0, 0, -1) );
}

TEST_CASE("applyRotationMatrix performs the manual row-major 3x3 multiply")
{
  const double M[9] = { 1.0, 2.0, 3.0,
                        4.0, 5.0, 6.0,
                        7.0, 8.0, 10.0 };
  pt::Vector v(1.0, -1.0, 2.0);
  pt::Vector res = v.applyRotationMatrix(M);
  CHECK( res.x() == 1.0 * 1.0 + 2.0 * -1.0 + 3.0 * 2.0 );
  CHECK( res.y() == 4.0 * 1.0 + 5.0 * -1.0 + 6.0 * 2.0 );
  CHECK( res.z() == 7.0 * 1.0 + 8.0 * -1.0 + 10.0 * 2.0 );
  CHECK( res == pt::Vector(5.0, 11.0, 19.0) );

  //Applying an identity matrix changes nothing:
  const double I[9] = { 1.0, 0.0, 0.0,
                        0.0, 1.0, 0.0,
                        0.0, 0.0, 1.0 };
  CHECK( v.applyRotationMatrix(I) == v );

  //Applying R to the basis vectors picks out the columns of R:
  double R[9];
  pt::Vector(1, 2, 3).findRotationMatrixFrom001(R);
  pt::Vector xhat(1, 0, 0), yhat(0, 1, 0), zhat(0, 0, 1);
  CHECK( xhat.applyRotationMatrix(R) == pt::Vector(R[0], R[3], R[6]) );
  CHECK( yhat.applyRotationMatrix(R) == pt::Vector(R[1], R[4], R[7]) );
  CHECK( zhat.applyRotationMatrix(R) == pt::Vector(R[2], R[5], R[8]) );
}
