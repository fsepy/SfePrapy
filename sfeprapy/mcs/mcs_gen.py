# -*- coding: utf-8 -*-

from io import StringIO

import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.interpolate import interp1d


def gumbel_r_(mean: float, sd: float, **_):
    # parameters Gumbel W&S
    alpha = 1.282 / sd
    u = mean - 0.5772 / alpha

    # parameters Gumbel scipy
    scale = 1 / alpha
    loc = u

    return dict(loc=loc, scale=scale)


def lognorm_(mean: float, sd: float, **_):
    cov = sd / mean

    sigma_ln = np.sqrt(np.log(1 + cov ** 2))
    miu_ln = np.log(mean) - 1 / 2 * sigma_ln ** 2

    s = sigma_ln
    loc = 0
    scale = np.exp(miu_ln)

    return dict(s=s, loc=loc, scale=scale)


def norm_(mean: float, sd: float, **_):
    loc = mean
    scale = sd

    return dict(loc=loc, scale=scale)


def uniform_(ubound: float, lbound: float, **_):
    if lbound > ubound:
        lbound += ubound
        ubound = lbound - ubound
        lbound -= ubound

    loc = lbound
    scale = ubound - lbound

    return dict(loc=loc, scale=scale)


def random_variable_generator(dict_in: dict, num_samples: int):
    """Generates samples of defined distribution. This is build upon scipy.stats library.

    :param dict_in:     distribution inputs, required keys are distribution dependent, should be align with inputs
                        required in the scipy.stats. Additional compulsory keys are:
                            `dist`: str, distribution type;
                            `ubound`: float, upper bound of the sampled values; and
                            `lbound`: float, lower bound of the sampled values.
    :param num_samples: number of samples to be generated.
    :return samples:    sampled values based upon `dist` in the range [`lbound`, `ubound`] with `num_samples` number of
                        values.
    """

    # assign distribution type
    dist_0 = dict_in["dist"]
    dist = dict_in["dist"]

    # assign distribution boundary (for samples)
    ubound = dict_in["ubound"]
    lbound = dict_in["lbound"]

    # sample CDF points (y-axis value)
    def generate_cfd_q(dist_, dist_kw_, lbound_, ubound_):
        cfd_q_ = np.linspace(
            getattr(stats, dist_).cdf(x=lbound_, **dist_kw_),
            getattr(stats, dist_).cdf(x=ubound_, **dist_kw_),
            num_samples,
        )
        samples_ = getattr(stats, dist_).ppf(q=cfd_q_, **dist_kw_)
        return samples_

    # convert human distribution parameters to scipy distribution parameters
    if dist_0 == "gumbel_r_":
        dist_kw = gumbel_r_(**dict_in)
        dist = "gumbel_r"
        samples = generate_cfd_q(
            dist_=dist, dist_kw_=dist_kw, lbound_=lbound, ubound_=ubound
        )
    elif dist_0 == "uniform_":
        dist_kw = uniform_(**dict_in)
        dist = "uniform"
        samples = generate_cfd_q(
            dist_=dist, dist_kw_=dist_kw, lbound_=lbound, ubound_=ubound
        )

    elif dist_0 == "norm_":
        dist_kw = norm_(**dict_in)
        dist = "norm"
        samples = generate_cfd_q(
            dist_=dist, dist_kw_=dist_kw, lbound_=lbound, ubound_=ubound
        )

    elif dist_0 == "lognorm_":
        dist_kw = lognorm_(**dict_in)
        dist = "lognorm"
        samples = generate_cfd_q(
            dist_=dist, dist_kw_=dist_kw, lbound_=lbound, ubound_=ubound
        )

    elif dist_0 == "lognorm_mod_":
        dist_kw = lognorm_(**dict_in)
        dist = "lognorm"
        samples = generate_cfd_q(
            dist_=dist, dist_kw_=dist_kw, lbound_=lbound, ubound_=ubound
        )
        samples = 1 - samples

    elif dist_0 == "car_cluster_size":
        '''
        derived from figure 13-4

        y = - 0.0099 x + 0.88
        int(y) = 0.88 x - 0.00495 x ** 2 + C
        Note C is zero cause y = 0 at x = 0

        CDF(car_cluster_size) = (9/352) * (0.88 * car_cluster_size - 0.00495 * car_cluster_size ** 2)
        Note the first factor make CDF = 1 at car cluster = 90

        car_cluster_size = 800/9 * (1 - (1-y)**0.5)
        '''
        y = np.linspace(0, 1, num_samples + 2)[1:-1]
        samples = np.floor(800 / 9 * (1 - (1 - y) ** 0.5))

    elif dist_0 == 'samples':
        v = dict_in.pop('values')
        samples = np.array([float(i.strip()) for i in v.split(',')])
        samples = samples[np.random.randint(low=0, high=len(samples), size=num_samples)]
        print(len(samples), samples)

    elif dist_0 == "constant_":
        # print(num_samples, lbound, ubound, np.average(lbound))
        samples = np.full((num_samples,), np.average([lbound, ubound]))

    else:
        try:
            dict_in.pop("dist")
            dict_in.pop("ubound")
            dict_in.pop("lbound")
            samples = generate_cfd_q(
                dist_=dist, dist_kw_=dict_in, lbound_=lbound, ubound_=ubound
            )
        except AttributeError:
            raise ValueError("Unknown distribution type {}.".format(dist))

    samples[samples == np.inf] = ubound
    samples[samples == -np.inf] = lbound

    if "permanent" in dict_in:
        samples += dict_in["permanent"]

    if "coefficient" in dict_in:
        samples *= dict_in['coefficient']

    np.random.shuffle(samples)

    return samples


def dict_unflatten(dict_in: dict) -> dict:
    dict_out = dict()

    for k in list(dict_in.keys()):
        if ":" in k:
            k1, k2 = k.split(":")

            if k1 in dict_out:
                dict_out[k1][k2] = dict_in[k]
            else:
                dict_out[k1] = dict(k2=dict_in[k])

    return dict_out


def dict_flatten(dict_in: dict) -> dict:
    """Converts two levels dict to single level dict. Example input and output see _test_dict_flatten.
    :param dict_in: Any two levels (or less) dict.
    :return dict_out: Single level dict.
    """

    dict_out = dict()

    for k in list(dict_in.keys()):
        if isinstance(dict_in[k], dict):
            for kk, vv in dict_in[k].items():
                dict_out[f"{k}:{kk}"] = vv
        else:
            dict_out[k] = dict_in[k]

    return dict_out


def main(x: dict, num_samples: int) -> pd.DataFrame:
    """Generates samples based upon prescribed distribution types.

    :param x: description of distribution function.
    :param num_samples: number of samples to be produced.
    :return df_out:
    """

    dict_out = dict()

    for k, v in x.items():

        if isinstance(v, float) or isinstance(v, int) or isinstance(v, np.float):
            dict_out[k] = np.full((num_samples,), v, dtype=float)

        elif isinstance(v, str):
            dict_out[k] = np.full(
                (num_samples,), v, dtype=np.dtype("U{:d}".format(len(v)))
            )

        elif isinstance(v, np.ndarray) or isinstance(v, list):
            dict_out[k] = list(np.full((num_samples, len(v)), v, dtype=float))

        elif isinstance(v, dict):
            if "dist" in v:
                try:
                    dict_out[k] = random_variable_generator(v, num_samples)
                except KeyError:
                    raise ("Missing parameters in input variable {}.".format(k))
            elif "ramp" in v:
                s_ = StringIO(v["ramp"])
                d_ = pd.read_csv(
                    s_,
                    names=["x", "y"],
                    dtype=float,
                    skip_blank_lines=True,
                    skipinitialspace=True,
                )
                t_ = d_.iloc[:, 0]
                v_ = d_.iloc[:, 1]
                if all(v_ == v_[0]):
                    f_interp = v_[0]
                else:
                    f_interp = interp1d(t_, v_, bounds_error=False, fill_value=0)
                dict_out[k] = np.full((num_samples,), f_interp)
            else:
                raise ValueError("Unknown input data type for {}.".format(k))
        else:
            raise TypeError("Unknown input data type for {}.".format(k))

    dict_out["index"] = np.arange(0, num_samples, 1)

    df_out = pd.DataFrame.from_dict(dict_out, orient="columns")

    return df_out
