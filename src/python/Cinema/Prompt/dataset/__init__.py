import GPy
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
from scipy.stats import qmc
from pyDOE import lhs
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from abc import ABC, abstractmethod
import requests

"""
    The goal of maximizing diversity in the dataset is to cover a wide range of the parameter space, 
    capturing different behaviors of the model. This helps in building a more robust model that generalizes 
    well across various scenarios. By selecting points where the GP is uncertain, you are effectively 
    exploring underrepresented regions of the parameter space, thereby increasing the diversity of your dataset.

    """


class SamplerMixin(ABC):
    @abstractmethod
    def sample(self, num_samples, num_parameters):
        pass

class LHSSamplerMixin(SamplerMixin):
    def sample(self, num_samples, num_parameters):
        return lhs(num_parameters, samples=num_samples)

class SobolSamplerMixin(SamplerMixin):
    def sample(self, num_samples, num_parameters):
        sobol_sampler = qmc.Sobol(d=num_parameters)
        return sobol_sampler.random_base2(m=int(np.log2(num_samples)))

class SensitivityAnalysisMixin:
    def sensitivity_analysis(self, outputs):
        flattened_outputs = [output.flatten() for output in outputs]
        scaler = StandardScaler()
        scaled_outputs = scaler.fit_transform(flattened_outputs)
        pca = PCA(n_components=1)
        pca.fit(scaled_outputs)
        return pca.components_[0]

class NetworkedModelSimulationMixin:
    def simulate_model(self, params):
        # Simulate sending parameters to a networked calculator
        response = requests.post("http://example.com/calculate", json={'params': params.tolist()})
        if response.status_code == 200:
            return np.array(response.json()['output'])
        else:
            raise ConnectionError("Failed to get response from the networked calculator")

class AdaptiveSparseGPSampler(LHSSamplerMixin, SensitivityAnalysisMixin, NetworkedModelSimulationMixin):
    def __init__(self, num_parameters, initial_samples, additional_samples, num_inducing=10, batch_size=5):
        self.num_parameters = num_parameters
        self.initial_samples = initial_samples
        self.additional_samples = additional_samples
        self.num_inducing = num_inducing
        self.batch_size = batch_size

    def perform_sampling(self):
        # Initial sampling
        initial_samples = self.sample(self.initial_samples, self.num_parameters)
        outputs = [self.simulate_model(sample) for sample in initial_samples]

        # Transform outputs to log space
        X_train = np.array(initial_samples)
        y_train_log = np.log(np.array([output.flatten() for output in outputs]) + 1e-10)

        # Fit initial Sparse GP model
        kernel = GPy.kern.RBF(input_dim=self.num_parameters)
        sparse_gp = GPy.models.SparseGPRegression(X_train, y_train_log[:, None], kernel, num_inducing=self.num_inducing)
        sparse_gp.optimize()

        # Iteratively add samples in batches and update the Sparse GP model
        num_batches = self.additional_samples // self.batch_size
        for _ in range(num_batches):
            batch_samples = []
            for _ in range(self.batch_size):
                # Predict with Sparse GP to find areas of high uncertainty
                X_candidates = self.sample(100, self.num_parameters)
                y_mean_log, y_var_log = sparse_gp.predict(X_candidates)
                y_std_log = np.sqrt(y_var_log)
                most_uncertain_idx = np.argmax(y_std_log)
                new_sample = X_candidates[most_uncertain_idx]
                batch_samples.append(new_sample)

            # Evaluate new samples
            new_outputs = [self.simulate_model(sample) for sample in batch_samples]

            # Update training data with the batch
            X_train = np.vstack((X_train, batch_samples))
            y_train_log = np.append(y_train_log, np.log(np.array([output.flatten() for output in new_outputs]) + 1e-10))

            # Update the Sparse GP model
            sparse_gp.set_XY(X_train, y_train_log[:, None])
            sparse_gp.optimize()

        return [np.exp(y) for y in y_train_log]  # Return outputs in original space
