/*
# <<BEGIN-copyright>>
# Copyright 2019, Lawrence Livermore National Security, LLC.
# See the top-level COPYRIGHT file for details.
# 
# SPDX-License-Identifier: MIT
# <<END-copyright>>
*/

#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <set>

#include <statusMessageReporting.h>

#include <MCGIDI.hpp>
#include "PTRandCanonical.hh"
#include "PTGidiSetting.hh"

class Bins {

    public:
        bool m_logDomainStep;
        double m_domainMin, m_domainMax, m_domainWidth;
        double m_logDomainFraction;
        long m_underFlows;
        long m_overFlows;
        std::vector<long> m_bins;
        double m_underFlowWeights;
        double m_overFlowWeights;
        std::vector<double> m_weightedBins;

        void setDomain( double a_domainMin, double a_domainMax ) {

            m_domainMin = a_domainMin;
            m_domainMax = a_domainMax;
            m_domainWidth = m_domainMax - m_domainMin;
            m_logDomainFraction = 2.0;
            if( m_logDomainStep ) m_logDomainFraction = log( pow( m_domainMax / m_domainMin, 1.0 / m_bins.size( ) ) );
        }

        Bins( long a_numberOfBins, double a_domainMin, double a_domainMax, bool a_logDomainStep = false ) :
                m_logDomainStep( a_logDomainStep ),
                m_underFlows( 0 ),
                m_overFlows( 0 ),
                m_bins( a_numberOfBins, 0 ),
                m_underFlowWeights( 0.0 ),
                m_overFlowWeights( 0.0 ),
                m_weightedBins( a_numberOfBins, 0.0 ) {

            setDomain( a_domainMin, a_domainMax );
        }

        void clear( ) {

            m_underFlows = 0;
            m_overFlows = 0;
            m_underFlowWeights = 0.0;
            m_overFlowWeights = 0.0;
            for( std::size_t i1 = 0; i1 < m_bins.size( ); ++i1 ) {
                m_bins[i1] = 0;
                m_weightedBins[i1] = 0.0;
            }
        }

        void accrue( double a_value, double a_weight = 1.0 ) {

            long index;

            if( a_value == m_domainMax ) {
                index = (long) m_bins.size( ) - 1; }
            else if( m_logDomainStep ) {
                index = (long) ( log( a_value / m_domainMin ) / m_logDomainFraction ); }
            else {
                index = (long) ( ( a_value - m_domainMin ) / m_domainWidth * m_bins.size( ) );
            }

            if( index < 0 ) {
                ++m_underFlows;
                m_underFlowWeights += a_weight; }
            else if( index >= (long) m_bins.size( ) ) {
                ++m_overFlows;
                m_overFlowWeights += a_weight; }
            else {
                ++m_bins[index];
                m_weightedBins[index] += a_weight;
            }
        }

        long total( bool a_includeOutOfBounds ) {
            long sum = 0;

            if( a_includeOutOfBounds ) sum += m_underFlows + m_overFlows;

            for( std::size_t i1 = 0; i1 < m_bins.size( ); ++i1 ) sum +=  m_bins[i1];

            return( sum );
        }

        double totalWeights( bool a_includeOutOfBounds ) {
            double sum = 0;

            if( a_includeOutOfBounds ) sum += m_underFlowWeights + m_overFlowWeights;

            for( std::size_t i1 = 0; i1 < m_weightedBins.size( ); ++i1 ) sum +=  m_weightedBins[i1];

            return( sum );
        }

        double meanX( ) {

            double _total = total( false );

            if( _total == 0 ) return( 0.0 );

            double mean_x = 0.0;
            for( std::size_t i1 = 0; i1 <  m_bins.size( ); ++i1 ) {
                double x1;

                if( m_logDomainStep ) {
                    x1 = m_domainMin * exp( m_logDomainFraction * ( i1 + 0.5 ) ); }
                else {
                    x1 = ( i1 + 0.5 ) / ( (double) m_bins.size( ) ) * m_domainWidth + m_domainMin;
                }
                mean_x += m_bins[i1] * x1;
            }

            return( mean_x / _total );
        }

        void print( FILE *a_fOut, char const *a_label, bool a_includeWeights = false ) {

            long _total = total( false );
            double weightedTotal = totalWeights( false );

            fprintf( a_fOut, "\n\n" );
            if( strlen( a_label ) > 0 ) fprintf( a_fOut, "%s\n", a_label );
            fprintf( a_fOut, "# total number of inflows = %ld\n", _total );
            fprintf( a_fOut, "# number of underflows = %ld\n", m_underFlows );
            fprintf( a_fOut, "# number of overflows = %ld\n", m_overFlows );
            fprintf( a_fOut, "# number of Bins = %lu\n", m_bins.size( ) );
            fprintf( a_fOut, "# domain min = %g\n", m_domainMin );
            fprintf( a_fOut, "# domain max = %g\n", m_domainMax );
            if( a_includeWeights ) {
                fprintf( a_fOut, "# total weight = %15.7e\n", weightedTotal );
                fprintf( a_fOut, "# underflow weight = %15.7e\n", m_underFlowWeights );
                fprintf( a_fOut, "# overflow weight = %15.7e\n", m_overFlowWeights );
            }
            fprintf( a_fOut, "# x-values                      pdf         counts       fraction" );
            if( a_includeWeights ) fprintf( a_fOut, "       weighted pdf       weights       weighted fraction" );
            fprintf( a_fOut, "\n" );

            if( _total == 0 ) _total = 1;
            if( weightedTotal == 0.0 ) weightedTotal = 1.0;
            double norm = m_domainWidth / ( m_bins.size( ) + 1 );
            for( std::size_t i1 = 0; i1 <  m_bins.size( ); ++i1 ) {
                double x1;
                double partial = m_bins[i1] / (double) _total;

                if( m_logDomainStep ) {
                    x1 = m_domainMin * exp( m_logDomainFraction * ( i1 + 0.5 ) );
                    norm = x1 * ( exp( m_logDomainFraction ) - 1 ); }
                else {
                    x1 = ( i1 + 0.5 ) / ( (double) m_bins.size( ) ) * m_domainWidth + m_domainMin;
                }

                fprintf( a_fOut, "%23.15e  %15.7e  %8ld  %15.7e", x1, partial / norm, m_bins[i1], partial );
                if( a_includeWeights ) {
                    partial = m_weightedBins[i1] / weightedTotal;

                    fprintf( a_fOut, "  %15.7e  %15.7e  %15.7e",  partial / norm, m_weightedBins[i1], partial );
                }
                fprintf( a_fOut, "\n" );
            }
        }
};


static char const *description = "For a protare, samples specified reaction (or all if specified reaction index is negative) many times (see option '-n') "
    "at the specified projectile energy, and creates an energy and angular spectrum for the specified outgoing particle (see options '--oid').";

// double myRNG( void *state );
void main2( int argc, char **argv );
/*
=========================================================
*/
int main( int argc, char **argv ) {

    try {
        main2( argc, argv );
        exit( EXIT_SUCCESS ); }
    catch (std::exception &exception) {
        std::cerr << exception.what( ) << std::endl; }
    catch (char const *str) {
        std::cout << str << std::endl; }
    catch (std::string &str) {
        std::cout << str << std::endl;
    }

    exit( EXIT_SUCCESS );
}
/*
=========================================================
*/
void main2( int argc, char **argv ) {

    
    unsigned long long seed = 1;
    GIDI::ExcludeReactionsSet reactionsToExclude;
    GIDI::Transporting::Particles particles;
    double temperature_keV_K = 2.582e-5;
    LUPI::StatusMessageReporting smr1;

    std::map<std::string, std::string> particlesAndGIDs;

    particlesAndGIDs[PoPI::IDs::neutron] = "LLNL_gid_4";
    // particlesAndGIDs["H1"] = "LLNL_gid_71";
    // particlesAndGIDs["H2"] = "LLNL_gid_71";
    // particlesAndGIDs["H3"] = "LLNL_gid_71";
    // particlesAndGIDs["He3"] = "LLNL_gid_71";
    // particlesAndGIDs["He4"] = "LLNL_gid_71";
    // particlesAndGIDs[PoPI::IDs::photon] = "LLNL_gid_70";



    GIDI::Construction::Settings construction( GIDI::Construction::ParseMode::all, GIDI::Construction::PhotoMode::nuclearAndAtomic );
    // GIDI::Protare *protare = parseTestOptions.protare( pops, "/home/xxcai1/git/cinema/external/ptdata/pops.xml", "/home/xxcai1/git/cinema/external/ptdata/all.map", construction, PoPI::IDs::neutron, "U235" );
    auto &gs = Prompt::Singleton<Prompt::GidiSetting>::getInstance();
    PoPI::Database pops(gs.getGidiPops() );
    GIDI::Map::Map map( gs.getGidiMap(), pops );

    GIDI::Protare *protare =  (GIDI::Protare *) map.protare( construction, pops, "n", "U236" ) ;

    // GIDI::Transporting::Settings incompleteParticlesSetting( protare->projectile( ).ID( ), GIDI::Transporting::DelayedNeutrons::on );
    // std::set<std::string> incompleteParticles;
    // protare->incompleteParticles( incompleteParticlesSetting, incompleteParticles );
    // std::cout << "# List of incomplete particles:";
    // for( auto iter = incompleteParticles.begin( ); iter != incompleteParticles.end( ); ++iter ) {
    //     std::cout << " " << *iter;
    // }
    // std::cout << std::endl;

    std::string productID = "n";
    long numberOfSamples = 1000000;
    long numberOfBins = 10;

    int reactionIndex = -1;
    double energy_in = 10;

    GIDI::Styles::TemperatureInfos temperatures = protare->temperatures( );
    std::string label( temperatures[0].heatedCrossSection( ) );
    MCGIDI::Transporting::MC MC( pops, protare->projectile( ).ID( ), &protare->styles( ), label, GIDI::Transporting::DelayedNeutrons::on, 20.0 );
    MC.setThrowOnError( false );
    MC.sampleNonTransportingParticles( true );
    MC.set_ignoreENDF_MT5(true);
    MC.want_URR_probabilityTables(true);


    for( std::map<std::string, std::string>::iterator iter = particlesAndGIDs.begin( ); iter != particlesAndGIDs.end( ); ++iter ) {
        GIDI::Transporting::Particle particle( iter->first );
        particles.add( particle );
    }


    // for( int i = 0; i < protare->numberOfReactions(); ++i ) 
    // {
    //   if(protare->reaction(i)->ENDF_MT()==2)
    //   {
    //     reactionsToExclude.emplace(i);
    //   }
    // }


    MCGIDI::DomainHash domainHash( 4000, 1e-8, 20 );
    MCGIDI::Protare *MCProtare = MCGIDI::protareFromGIDIProtare( smr1, *protare, pops, MC, particles, domainHash, temperatures, reactionsToExclude );
  


    if( reactionIndex > static_cast<int>( MCProtare->numberOfReactions( ) ) ) {
        std::cout << "List of reaction indices, thresholds and labels are:" << std::endl;
        for( reactionIndex = 0; reactionIndex < static_cast<int>( MCProtare->numberOfReactions( ) ); ++reactionIndex ) {
            MCGIDI::Reaction const *reaction = MCProtare->reaction( reactionIndex );

            std::cout << std::setw( 4 ) << reactionIndex << "  " << std::to_string(  reaction->crossSectionThreshold( ) ) << "  " << reaction->label( ).c_str( ) << std::endl;
        }
        delete protare;
        delete MCProtare;
        exit( EXIT_SUCCESS );
    }

    int oidIndex = -1;
    int maxProductIndex = 0;
    for( auto particleIter = particles.particles( ).begin( ); particleIter != particles.particles( ).end( );  ++particleIter, ++maxProductIndex ) {
        MCProtare->setUserParticleIndex( pops[(*particleIter).first], maxProductIndex );
        if( (*particleIter).first == productID ) oidIndex = maxProductIndex;
        std::cout << "# particle ID/index " << (*particleIter).first << " " << maxProductIndex << std::endl;
    }

    int hashIndex = domainHash.index( energy_in );

    std::cout << "# path is " << protare->realFileName( ) << std::endl;
    std::cout << "# projectile is " << MCProtare->projectileID( ).c_str( ) << std::endl;
    std::cout << "# target is " << MCProtare->targetID( ).c_str( ) << std::endl;
    std::cout << "# projectile energy is " << energy_in << " MeV" << std::endl;
    if( reactionIndex >= 0 ) {
        MCGIDI::Reaction const *reaction = MCProtare->reaction( reactionIndex );
        std::cout << "# Reaction Info:" << std::endl;
        std::cout << "#     index: " << reactionIndex << std::endl;
        std::cout << "#     label: " << reaction->label( ).c_str( ) << std::endl;
        std::cout << "#     threshold: " << std::to_string(reaction->crossSectionThreshold( ) ) << std::endl;
    }

    // MCGIDI::Sampling::ClientCodeRNGData clientCodeRNGData( float64RNG64, nullptr );

    double energyMin = 1e-11;
    double energyMax = 20;
    Bins energyBins( numberOfBins, energyMin, energyMax, true );
    Bins muBins( numberOfBins, -1.0, 1.0 );

    MCGIDI::URR_protareInfos URR_protareInfos;
    double totalCrossSection = 0.0;
    MCGIDI::Sampling::Input input( false, MCGIDI::Sampling::Upscatter::Model::B );           // This should be an input option.
    MCGIDI::Sampling::StdVectorProductHandler products;
    if( reactionIndex < 0 ) {
        totalCrossSection = MCProtare->crossSection( URR_protareInfos, hashIndex, temperature_keV_K, energy_in, true ); }
    else {
        MCGIDI::Reaction const *reaction = MCProtare->reaction( reactionIndex );
        if( reaction->crossSectionThreshold( ) > energy_in ) {
            delete protare;
            delete MCProtare;

            exit( EXIT_SUCCESS );
        }
    }

    for( long sampleIndex = 0; sampleIndex < numberOfSamples; ++sampleIndex ) {
        int reactionIndex2 = reactionIndex;
        if( reactionIndex2 < 0 ) {
            // gidiplus 3.35: temperature/energy ride in Sampling::Input and the user RNG
            // is a callable. The temperature is passed through unchanged from the
            // pre-3.35 code (its keV-vs-MeV value is preserved as-is; see issue list).
            input.setTemperatureAndEnergy( temperature_keV_K, energy_in );
            reactionIndex2 = static_cast<int>( MCProtare->sampleReaction( input, URR_protareInfos, hashIndex, totalCrossSection,
                                                                          []() -> double { return getRandNumber(nullptr); } ) );
        }
        MCGIDI::Reaction const *reaction = MCProtare->reaction( reactionIndex2 );

        // if( recordPath != "" ) recordStream << "Event: " << reactionIndex2 << std::endl;

        products.clear( );

        reaction->sampleProducts( MCProtare, input,
                                  []() -> double { return getRandNumber(nullptr); },
                                  [&products]( MCGIDI::Sampling::Product &aproduct ) { products.push_back( aproduct ); },
                                  products );
        for( std::size_t productIndex = 0; productIndex < products.size( ); ++productIndex ) {
            MCGIDI::Sampling::Product const &product = products[productIndex];
            int userProductIndex = product.m_userProductIndex;
            // if( recordPath != "" ) {
            //     recordStream << "    product index: " << userProductIndex << " " << product.m_kineticEnergy << " " << product.m_px_vx << " " << product.m_py_vy << " " << product.m_pz_vz << std::endl;
            // }
            if( userProductIndex != oidIndex ) continue;
            
            energyBins.accrue( product.m_kineticEnergy, 1.0 );
            double speed = sqrt( product.m_px_vx * product.m_px_vx + product.m_py_vy * product.m_py_vy + product.m_pz_vz * product.m_pz_vz );
            double mu = 0.0;
            if( speed != 0.0 ) mu = product.m_pz_vz / speed;
            muBins.accrue( mu, 1.0 );
        }
    }

    energyBins.print( stdout, "# energy", true );
    muBins.print( stdout, "# mu", true );

    delete protare;
    delete MCProtare;
    // if( recordPath != "" ) {
    //     recordStream.close();
    // }

    exit( EXIT_SUCCESS );
}
