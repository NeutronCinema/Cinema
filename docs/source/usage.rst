Usage
=====

.. _installation:

Installation
------------

To use Cinema, first install it using pip:

.. code-block:: console

   (.venv) $ pip install Cinema

Creating recipes
----------------

To retrieve a list of random ingredients,
you can use the ``Cinema.get_random_ingredients()`` function:

.. autofunction:: Cinema.get_random_ingredients

The ``kind`` parameter should be either ``"meat"``, ``"fish"``,
or ``"veggies"``. Otherwise, :py:func:`Cinema.get_random_ingredients`
will raise an exception.

.. autoexception:: Cinema.InvalidKindError

For example:

>>> import Cinema
>>> Cinema.get_random_ingredients()
['shells', 'gorgonzola', 'parsley']

