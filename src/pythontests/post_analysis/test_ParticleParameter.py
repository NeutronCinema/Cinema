#!/usr/bin/env python3

from Cinema.analysis import ParticleParameter


def test_particle_parameter():
    quantity_str = 'time'
    quantity = ParticleParameter(quantity_str)
    from_unitstr = 'us'
    to_unitstr = 'ms'

    print(quantity.unit)
    print(quantity.get_conversion_factor(to_unitstr))

    print(quantity.unit.from_str(from_unitstr))

    print(quantity.unit.get_default())
    print(quantity.unit.from_str(from_unitstr).convert_to(1, quantity.unit.from_str(to_unitstr)))
