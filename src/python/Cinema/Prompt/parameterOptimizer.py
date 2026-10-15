#!/usr/bin/env python3

################################################################################
##                                                                            ##
##  This file is part of Cinema (code.ihep.ac.cn/cinema-developers/cinema)    ##
##                                                                            ##
##  Copyright 2021-2026 Cinema developers                                     ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################

import warnings


class Parameter:
    def __init__(self, name : str, lower, upper, promptval) -> None:
        self.name = name
        self.upper_lim = upper
        self.lower_lim = lower
        self.promptval = promptval
        if self.promptval>self.upper_lim or self.promptval<self.lower_lim:
            raise RuntimeError(f'promptval {promptval} is not in the range [{self.lower_lim},{self.upper_lim}]')
        if self.lower_lim>=self.upper_lim:
            raise RuntimeError(f'wrong parameter range [{self.lower_lim},{self.upper_lim}]')


    def get(self, trail = None):
        if trail:
            return trail.suggest_float(self.name, self.lower_lim, self.upper_lim)
        else:
            return self.promptval
        
    def __repr__(self) -> str:
        return f'Parameter "{self.name}", [{self.lower_lim},{self.upper_lim}], Prompt value {self.promptval}\n'
     
def analysisdb(study=None, name=None, target=None, storage=None ):
    if study is None:
        import optuna
        study = optuna.load_study(study_name=name, storage=storage)
    
    # Visualize the optimization history.
    from optuna.visualization import plot_contour
    from optuna.visualization import plot_intermediate_values
    from optuna.visualization import plot_optimization_history
    from optuna.visualization import plot_parallel_coordinate
    from optuna.visualization import plot_param_importances
    from optuna.visualization import plot_slice
    plot_optimization_history(study, target=target).show()

    # Visualize the learning curves of the trials.
    # plot_intermediate_values(study).show()

    # Visualize high-dimensional parameter relationships.
    plot_parallel_coordinate(study, target=target).show()

    # # Select parameters to visualize.
    # plot_parallel_coordinate(study, params=["x", "y"]).show()

    # Visualize hyperparameter relationships.
    plot_contour(study, target=target).show()

    # # Select parameters to visualize.
    # plot_contour(study, params=["x", "y"]).show()

    # Visualize individual hyperparameters.
    plot_slice(study, target=target).show()

    # # Select parameters to visualize.
    # plot_slice(study, params=["x", "y"]).show()

    # Visualize parameter importances.
    plot_param_importances(study, target=target).show()



class Optimiser:
    def __init__(self, sim, trailNeutronNum=1e5, directions= ["maximize"]) -> None:
        self.parameters = []
        self.sim = sim
        self.trailNeutronNum = trailNeutronNum
        self.directions = directions

    def addParameter(self, name, lower, upper, val=None):
        if val is None:
            val = 0.5*(lower + upper)
        self.parameters.append(Parameter(name, lower, upper, val))

    def getParameters(self, trail = None):
        l = {}
        for p in self.parameters:
            l[p.name] =p.get(trail)
        return l       

    def objective(self, trial):
        raise NotImplementedError('')

    def visInitialGeometry(self, num=100):
        self.sim.clear() 
        self.sim.makeWorld(self.getParameters())
        self.sim.show(int(num))


    def optimize(self, name, n_trials, localhost=False, storage=None):
        """
        Run the optuna study.

        Args:
            name: Study name
            n_trials: Number of optimization trials
            localhost: Deprecated. With no storage URL it selects the
                in-memory study; an explicit storage URL always wins and the
                flag only triggers the deprecation warning.
            storage: Optuna storage URL (e.g. 'sqlite:///optuna_study.db') for
                a persistent study. Required unless localhost=True (deprecated)
                selects a process-local in-memory study.

        Returns:
            optuna.Study: The finished study
        """
        import optuna
        if localhost:
            warnings.warn('localhost is deprecated; pass a storage URL such as '
                          '"sqlite:///optuna_study.db" for a persistent study '
                          '(the in-memory study selected by localhost=True dies '
                          'with the process)',
                          FutureWarning, stacklevel=2)
        elif storage is None:
            raise ValueError('no optuna storage given: the former remote-MySQL '
                             'default was removed for security reasons. Pass '
                             'storage="sqlite:///optuna_study.db" (or any optuna '
                             'storage URL) to persist the study; a process-local '
                             'in-memory study is only available via the '
                             'deprecated localhost=True')

        if storage is None:
            # in-memory study, dies with the process
            self.study = optuna.create_study(study_name=name,
                                    directions=self.directions
                                    )
        else:
            self.study = optuna.create_study(study_name=name,
                                            storage=storage,
                                            directions=self.directions,
                                            load_if_exists=True
                                            )


        self.study.optimize(self.objective, n_trials)

        return self.study
    
    def analysis(self):
        analysisdb(self.study)
    

    def optimize_botorch(self, name, n_trials, localhost=False, storage=None):
        from botorch.settings import validate_input_scaling
        import optuna

        # Show warnings from BoTorch such as unnormalized input data warnings.
        validate_input_scaling(True)

        sampler = optuna.integration.BoTorchSampler(
            n_startup_trials=int(n_trials*0.5),
        )

        if localhost:
            warnings.warn('localhost is deprecated; pass a storage URL such as '
                          '"sqlite:///optuna_study.db" for a persistent study '
                          '(the in-memory study selected by localhost=True dies '
                          'with the process)',
                          FutureWarning, stacklevel=2)
        elif storage is None:
            raise ValueError('no optuna storage given: the former remote-MySQL '
                             'default was removed for security reasons. Pass '
                             'storage="sqlite:///optuna_study.db" (or any optuna '
                             'storage URL) to persist the study; a process-local '
                             'in-memory study is only available via the '
                             'deprecated localhost=True')

        if storage is None:
            # in-memory study, dies with the process
            self.study = optuna.create_study(study_name=name,
                                    directions=self.directions,
                                    sampler=sampler
                                    )
        else:
            self.study = optuna.create_study(
                study_name=name,
                storage=storage,
                directions=self.directions,
                sampler=sampler,
                load_if_exists=True
            )

        self.study.optimize(self.objective, n_trials=n_trials)

        return self.study