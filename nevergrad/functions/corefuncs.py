# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict, Any, Tuple, List, Callable
from math import exp, sqrt, tanh
import numpy as np
from .utils import PostponedObject
from ..instrumentation import discretization
from ..common.decorators import Registry


registry = Registry[Callable[[np.ndarray], float]]()


def _onemax(x: List[int]) -> float:
    """onemax(x) is the most classical case of discrete functions, adapted to minimization.

    It is originally designed for lists of bits. It just counts the number of 1,
    and returns len(x) - number of ones..
    It also works in the continuous case but in that cases discretizes the
    input domain by ]0.5,1.5] --> 1 and 0 everywhere else.
    """
    return len(x) - sum(1 if int(round(w)) == 1 else 0 for w in x)


def _leadingones(x: List[int]) -> float:
    """leadingones is the second most classical discrete function, adapted for minimization.

    Returns len(x) - number of initial 1. I.e.
    leadingones([0 1 1 1]) = 4,
    leadingones([1 1 1 1]) = 0,
    leadingones([1 0 0 0]) = 1.
    """
    for i, x_ in enumerate(list(x)):
        if int(round(x_)) != 1:
            return len(x) - i
    return 0


def _jump(x: List[int]) -> float:  # TODO: docstring?
    """There exists variants of jump functions; we are in minimization.

    The principle of a jump function is that local descent does not succeed.
    Jumps are necessary.
    """
    n = len(x)
    m = n // 4
    o = n - _onemax(x)
    if o == n or o <= n - m:
        return n - m - o
    return o  # Deceptive part.


def _styblinksitang(x: np.ndarray, noise: float) -> float:
    """Classical function for testing noisy optimization."""
    x2 = x ** 2
    val = x2.dot(x2) + np.sum(5 * x - 16 * x2)
    # return a positive value for maximization
    return float(39.16599 * len(x) + 0.5 * val + noise * np.random.normal(size=val.shape))


class DelayedSphere(PostponedObject):
    def __call__(self, x: np.ndarray) -> float:
        return float(np.sum(x ** 2))

    def get_postponing_delay(self, args: Tuple[Any, ...], kwargs: Dict[str, Any], value: float) -> float:
        x = args[0]
        return float(abs(1.0 / x[0]) / 1000.0) if x[0] != 0.0 else 0.0


registry.register(DelayedSphere())


@registry.register
def sphere(x: np.ndarray) -> float:
    """The most classical continuous optimization testbed.

    If you do not solve that one then you have a bug."""
    assert x.ndim == 1
    return float(x.dot(x))


@registry.register
def sphere1(x: np.ndarray) -> float:
    """Translated sphere function."""
    return sphere(x - 1.0)


@registry.register
def sphere2(x: np.ndarray) -> float:
    """A bit more translated sphere function."""
    return sphere(x - 2.0)


@registry.register
def sphere4(x: np.ndarray) -> float:
    """Even more translated sphere function."""
    return sphere(x - 4.0)


@registry.register
def maxdeceptive(x: np.ndarray) -> float:
    dec = 3 * x ** 2 - (2 / (3 ** (x - 2) ** 2 + 0.1))
    return float(np.max(dec))


@registry.register
def sumdeceptive(x: np.ndarray) -> float:
    dec = 3 * x ** 2 - (2 / (3 ** (x - 2) ** 2 + 0.1))
    return float(np.sum(dec))


@registry.register
def altcigar(x: np.ndarray) -> float:
    """Similar to cigar, but variables in inverse order.

    E.g. for pointing out algorithms not invariant to the order of variables."""
    return float(x[-1]) ** 2 + 1000000.0 * sphere(x[:-1])


@registry.register
def cigar(x: np.ndarray) -> float:
    """Classical example of ill conditioned function.

    The other classical example is ellipsoid.
    """
    return float(x[0]) ** 2 + 1000000.0 * sphere(x[1:])


@registry.register
def altellipsoid(y: np.ndarray) -> float:
    """Similar to Ellipsoid, but variables in inverse order.

    E.g. for pointing out algorithms not invariant to the order of variables."""
    return ellipsoid(y[::-1])


@registry.register
def ellipsoid(x: np.ndarray) -> float:
    """Classical example of ill conditioned function.

    The other classical example is cigar.
    """
    dim = x.size
    weights = 10 ** np.linspace(0, 6, dim)
    return float(weights.dot(x ** 2))


@registry.register
def rastrigin(x: np.ndarray) -> float:
    """Classical multimodal function."""
    cosi = float(np.sum(np.cos(2 * np.pi * x)))
    return float(10 * (len(x) - cosi) + sphere(x))


@registry.register
def hm(x: np.ndarray) -> float:
    """New multimodal function (proposed for Nevergrad)."""
    return float((x ** 2).dot(1.1 + np.cos(1.0 / x)))


@registry.register
def rosenbrock(x: np.ndarray) -> float:
    x_m_1 = x[:-1] - 1
    x_diff = x[:-1] ** 2 - x[1:]
    return float(100 * x_diff.dot(x_diff) + x_m_1.dot(x_m_1))


def ackley(x: np.ndarray) -> float:
    dim = x.size
    sum_cos = np.sum(np.cos(2 * np.pi * x))
    return -20.0 * exp(-0.2 * sqrt(sphere(x) / dim)) - exp(sum_cos / dim) + 20 + exp(1)


def schwefel_1_2(x: np.ndarray) -> float:
    cx = np.cumsum(x)
    return sphere(cx)


@registry.register
def griewank(x: np.ndarray) -> float:
    """Multimodal function, often used in Bayesian optimization."""
    part1 = sphere(x)
    part2 = np.prod(np.cos(x / np.sqrt(1 + np.arange(len(x)))))
    return 1 + (float(part1) / 4000.0) - float(part2)


@registry.register
def deceptiveillcond(x: np.ndarray) -> float:
    """An extreme ill conditioned functions. Most algorithms fail on this.

    The condition number increases to infinity as we get closer to the optimum."""
    assert len(x) >= 2
    return float(
        max(np.abs(np.arctan(x[1] / x[0])), np.sqrt(x[0] ** 2.0 + x[1] ** 2.0), 1.0 if x[0] > 0 else 0.0) if x[0] != 0.0 else float("inf")
    )


@registry.register
def deceptivepath(x: np.ndarray) -> float:
    """A function which needs following a long path. Most algorithms fail on this.

    The path becomes thiner as we get closer to the optimum."""
    assert len(x) >= 2
    distance = np.sqrt(x[0] ** 2 + x[1] ** 2)
    if distance == 0.0:
        return 0.0
    angle = np.arctan(x[0] / x[1]) if x[1] != 0.0 else np.pi / 2.0
    invdistance = (1.0 / distance) if distance > 0.0 else 0.0
    if np.abs(np.cos(invdistance) - angle) > 0.1:
        return 1.0
    return float(distance)


@registry.register
def deceptivemultimodal(x: np.ndarray) -> float:
    """Infinitely many local optima, as we get closer to the optimum."""
    assert len(x) >= 2
    distance = np.sqrt(x[0] ** 2 + x[1] ** 2)
    if distance == 0.0:
        return 0.0
    angle = np.arctan(x[0] / x[1]) if x[1] != 0.0 else np.pi / 2.0
    invdistance = int(1.0 / distance) if distance > 0.0 else 0.0
    if np.abs(np.cos(invdistance) - angle) > 0.1:
        return 1.0
    return float(distance)


@registry.register
def lunacek(x: np.ndarray) -> float:
    """Multimodal function.

    Based on https://www.cs.unm.edu/~neal.holts/dga/benchmarkFunction/lunacek.html."""
    problemDimensions = len(x)
    s = 1.0 - (1.0 / (2.0 * np.sqrt(problemDimensions + 20.0) - 8.2))
    mu1 = 2.5
    mu2 = -np.sqrt(abs((mu1 ** 2 - 1.0) / s))
    firstSum = 0.0
    secondSum = 0.0
    thirdSum = 0.0
    for i in range(problemDimensions):
        firstSum += (x[i] - mu1) ** 2
        secondSum += (x[i] - mu2) ** 2
        thirdSum += 1.0 - np.cos(2 * np.pi * (x[i] - mu1))
    return min(firstSum, 1.0 * problemDimensions + secondSum) + 10 * thirdSum


# following functions using discretization should not be used with translation/rotation


@registry.register_with_info(no_transfrom=True)
def hardonemax(y: np.ndarray) -> float:
    """Onemax, with a discretization in 2 by threshold 0 (>0 or <0)."""
    return _onemax(discretization.threshold_discretization(y))


@registry.register_with_info(no_transfrom=True)
def hardjump(y: np.ndarray) -> float:
    """Hardjump, with a discretization in 2 by threshold 0 (>0 or <0)."""
    return _jump(discretization.threshold_discretization(y))


@registry.register_with_info(no_transfrom=True)
def hardleadingones(y: np.ndarray) -> float:
    """Leading ones, with a discretization in 2 by threshold 0 (>0 or <0)."""
    return _leadingones(discretization.threshold_discretization(y))


@registry.register_with_info(no_transfrom=True)
def hardonemax5(y: np.ndarray) -> float:
    """Hardonemax, with a discretization by 5 with 4 thresholds (quantiles of Gaussian)."""
    return _onemax(discretization.threshold_discretization(y, 5))


@registry.register_with_info(no_transfrom=True)
def hardjump5(y: np.ndarray) -> float:
    """Jump, with a discretization by 5 with 4 thresholds (quantiles of Gaussian)."""
    return _jump(discretization.threshold_discretization(y, 5))


@registry.register_with_info(no_transfrom=True)
def hardleadingones5(y: np.ndarray) -> float:
    """Leadingones, with a discretization by 5 with 4 thresholds (quantiles of Gaussian)."""
    return _leadingones(discretization.threshold_discretization(y, 5))


@registry.register_with_info(no_transfrom=True)
def onemax(y: np.ndarray) -> float:
    """Softmax discretization of onemax (This multiplies the dimension by 2)."""
    return _onemax(discretization.softmax_discretization(y))


@registry.register_with_info(no_transfrom=True)
def jump(y: np.ndarray) -> float:
    """Softmax discretization of jump (This multiplies the dimension by 2)."""
    return _jump(discretization.softmax_discretization(y))


@registry.register_with_info(no_transfrom=True)
def leadingones(y: np.ndarray) -> float:
    """Softmax discretization of leadingones (This multiplies the dimension by 2)."""
    return _leadingones(discretization.softmax_discretization(y))


@registry.register_with_info(no_transfrom=True)
def onemax5(y: np.ndarray) -> float:
    """Softmax discretization of onemax with 5 possibles values.

    This multiplies the dimension by 5."""
    return _onemax(discretization.softmax_discretization(y, 5))


@registry.register_with_info(no_transfrom=True)
def jump5(y: np.ndarray) -> float:
    """Softmax discretization of jump with 5 possibles values.

    This multiplies the dimension by 5."""
    return _jump(discretization.softmax_discretization(y, 5))


@registry.register_with_info(no_transfrom=True)
def leadingones5(y: np.ndarray) -> float:
    """Softmax discretization of leadingones with 5 possibles values.

    This multiplies the dimension by 5."""
    return _leadingones(discretization.softmax_discretization(y, 5))


@registry.register_with_info(no_transfrom=True)
def genzcornerpeak(y: np.ndarray) -> float:
    """One of the Genz functions, originally used in integration,

    tested in optim because why not."""
    value = float(1 + np.mean(np.tanh(y)))
    if value == 0:
        return float("inf")
    return value ** (-len(y) - 1)


@registry.register_with_info(no_transfrom=True)
def minusgenzcornerpeak(y: np.ndarray) -> float:
    """One of the Genz functions, originally used in integration,

    tested in optim because why not."""
    return -genzcornerpeak(y)


@registry.register
def genzgaussianpeakintegral(x: np.ndarray) -> float:
    """One of the Genz functions, originally used in integration,

    tested in optim because why not."""
    return exp(-sphere(x) / 4.0)


@registry.register
def minusgenzgaussianpeakintegral(x: np.ndarray) -> float:
    """One of the Genz functions, originally used in integration,

    tested in optim because why not."""
    return -genzgaussianpeakintegral(x)


@registry.register
def slope(x: np.ndarray) -> float:
    return sum(x)


@registry.register
def linear(x: np.ndarray) -> float:
    return tanh(x[0])


@registry.register
def st0(x: np.ndarray) -> float:
    """Styblinksitang function with 0 noise."""
    return _styblinksitang(x, 0)


@registry.register
def st1(x: np.ndarray) -> float:
    """Styblinksitang function with noise 1."""
    return _styblinksitang(x, 1)


@registry.register
def st10(x: np.ndarray) -> float:
    """Styblinksitang function with noise 10."""
    return _styblinksitang(x, 10)


@registry.register
def st100(x: np.ndarray) -> float:
    """Styblinksitang function with noise 100."""
    return _styblinksitang(x, 100)
