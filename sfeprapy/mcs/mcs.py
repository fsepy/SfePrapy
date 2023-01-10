# Monte Carlo Simulation Multiple Process Implementation
# Yan Fu, October 2017

import copy
import multiprocessing as mp
import os
import time
from abc import ABC, abstractmethod
from typing import Union, Callable

import pandas as pd
from tqdm import tqdm

from .mcs_gen import main as mcs_gen_main


class MCS(ABC):
    """
    Monte Carlo Simulation (MCS) object defines the framework of a MCS process. MCS is designed to work as parent class
    and certain methods defined in this class are placeholders.

    To help to understand this class, a brief process of a MCS are outlined below:

        1. stochastic problem definition (i.e. raw input parameters from the user).
        2. sample deterministic parameters from the stochastic inputs
        3. iterate the sampled parameters and run deterministic calculation
        4. summarise results

    Following above, this object consists of four primary methods, each matching one of the above step:

        `MCS.mcs_inputs`
            A method to intake user inputs, restructure data so usable within MCS.
        `MCS.mcs_sampler`
            A method to sample deterministic parameters from the stochastic parameters, produces input to be used in
            the next step.
        `MCS.mcs_deterministic_calc`
            A method to carry out deterministic calculation.
            NOTE! This method needs to be re-defined in a child class.
        `MCS.mcs_post_per_case`
            A method to post-processing results.
            NOTE! This method needs to be re-defined in a child class.
    """
    DEFAULT_TEMP_FOLDER_NAME = "mcs.out"
    DEFAULT_MCS_OUTPUT_FILE_NAME = "mcs.out.csv"

    def __init__(self, n_procs: int = 1):
        # Assign user defined properties
        if isinstance(n_procs, int) and n_procs > 0:
            self.n_threads = n_procs
        else:
            raise ValueError('`n_procs` must be an integer greater than zero')

        # Assign other properties
        self.cwd: str = None  # work folder path
        self.__mcs_inputs: dict = None  # input parameters
        self.outputs: pd.DataFrame = None

        # Assign default properties
        self.func_mcs_gen = mcs_gen_main

    @property
    def inputs(self) -> dict:
        return self.__mcs_inputs

    @inputs.setter
    def inputs(self, fp_df_dict: Union[str, pd.DataFrame, dict]):
        """
        :param fp_df_dict:
        :return:
        """
        if isinstance(fp_df_dict, str):
            '''
            If a string is provided, regard as full spreadsheet file path.
            Currently support *.csv, *.xls and *.xlsx
            '''
            if self.cwd is None:
                self.cwd = os.path.dirname(fp_df_dict)
            self.__mcs_inputs = self.read_spreadsheet_input(fp_df_dict)
        elif isinstance(fp_df_dict, pd.DataFrame):
            mcs_inputs = fp_df_dict.to_dict()
            for k in list(mcs_inputs.keys()):
                if 'case_name' not in mcs_inputs[k]:
                    mcs_inputs[k]['case_name'] = k
            self.__mcs_inputs = mcs_inputs
        elif isinstance(fp_df_dict, dict):
            self.__mcs_inputs = fp_df_dict
        else:
            raise TypeError("Unknown input data type.")

    @abstractmethod
    def mcs_deterministic_calc(self, *args, **kwargs) -> dict:
        """Placeholder method. The Monte Carlo Simulation deterministic calculation routine.
        :return:
        """
        raise NotImplementedError('This method should be overridden by a child class')

    @abstractmethod
    def mcs_deterministic_calc_mp(self, *args, **kwargs) -> dict:
        """Placeholder method. The Monte Carlo Simulation deterministic calculation routine.
        :return:
        """
        raise NotImplementedError('This method should be overridden by a child class')

    def run(
            self, cases_to_run=None, keep_results: bool = False,
            set_prog: Callable = None, set_prog_max: Callable = None, set_prog_complete: Callable = None,
            *args, **kwargs
    ):
        # ----------------------------
        # Prepare mcs parameter inputs
        # ----------------------------
        # elevate dict dimension, for example
        # {
        #   'fuel_load:lbound': 100,
        #   'fuel_load:ubound': 200
        # }
        # became
        # {
        #   'fuel_load': {
        #       'lbound': 100,
        #       'ubound': 200
        #    }
        # }
        if cases_to_run is not None:
            x1 = self.inputs
            for k in list(x1.keys()):
                if k not in cases_to_run:
                    x1.pop(k)
        else:
            x1 = self.inputs
        for case_name in list(x1.keys()):
            for param_name in list(x1[case_name].keys()):
                if ":" in param_name:
                    param_name_parent, param_name_sibling = param_name.split(":")
                    if param_name_parent not in x1[case_name]:
                        x1[case_name][param_name_parent] = dict()
                    x1[case_name][param_name_parent][param_name_sibling] = x1[case_name].pop(param_name)
        # to convert all "string numbers" to float data type
        for case_name in x1.keys():
            for i, v in x1[case_name].items():
                if isinstance(v, dict):
                    for ii, vv in v.items():
                        try:
                            x1[case_name][i][ii] = float(vv)
                        except:
                            pass
                else:
                    try:
                        x1[case_name][i] = float(v)
                    except:
                        pass

        # ------------------------------
        # Generate mcs parameter samples
        # ------------------------------
        x2 = dict()
        for k, v in x1.items():
            x2[k] = self.func_mcs_gen(v, int(v['n_simulations']))
            # try:
            #     x2[k] = self.func_mcs_gen(v, int(v['n_simulations']))
            # except Exception as e:
            #     raise ValueError(f'Failed to generate stochastic samples from user defined inputs for case {k}, {e}')

        # ------------------
        # Run mcs simulation
        # ------------------
        x3 = dict()  # output container, structure:
        # {
        #   'case_1': df1,
        #   'case_2': df2
        # }

        m, p = mp.Manager(), mp.Pool(self.n_threads, maxtasksperchild=1000)
        if set_prog_max:
            set_prog_max(sum(len(i.index) for i in x2.values()))

        progress_tracker = 0
        for i, k in enumerate(x2.keys()):
            v = x2[k]
            x3_ = self.__mcs_mp(
                self.mcs_deterministic_calc,
                self.mcs_deterministic_calc_mp,
                x=v,
                n_threads=self.n_threads,
                m=m,
                p=p,
                set_prog=set_prog,
                set_prog_init=progress_tracker,
            )

            progress_tracker += len(v.index)

            # Post process output upon completion per case
            if self.post_case is not None:
                self.post_case(df=x3_, *args, **kwargs)

            if keep_results is True:
                x3[k] = copy.copy(x3_)

        p.close()
        p.join()
        if set_prog_complete:
            set_prog_complete(True)

        # ------------
        # Pack results
        # ------------
        if keep_results is True:
            self.outputs = pd.concat([v for v in x3.values()], ignore_index=True)
        else:
            self.outputs = None

        # Post process output upon completion of all cases
        # self.mcs_post_all_cases(self.__mcs_out)

    @abstractmethod
    def post_case(self, *arg, **kwargs):
        """
        This method will be called upon completion of each case
        """
        raise NotImplementedError('This method should be overridden by a child class')

    @abstractmethod
    def post_all(self, *args, **kwargs):
        """
        This method will be called upon completion of all cases
        """
        raise NotImplementedError('This method should be overridden by a child class')

    @staticmethod
    def __mcs_mp(
            func, func_mp, x: pd.DataFrame, n_threads: int, m, p, set_prog: Callable = None, set_prog_init: int = 0,
            enable_tqdm: bool = True,
    ) -> pd.DataFrame:
        list_mcs_in = x.to_dict(orient="records")

        n_simulations = len(list_mcs_in)
        if n_threads == 1 or func_mp is None:
            mcs_out = list()
            j = 0
            for i in tqdm(list_mcs_in, ncols=60, disable=~enable_tqdm):
                mcs_out.append(func(**i))
                j += 1
                if set_prog is not None:
                    set_prog(int(j + set_prog_init))
        else:
            q = m.Queue()
            jobs = p.map_async(func_mp, [(dict_, q) for dict_ in list_mcs_in])

            with tqdm(total=n_simulations, ncols=60, disable=~enable_tqdm) as pbar:
                while True:
                    if jobs.ready():
                        if n_simulations > pbar.n:
                            pbar.update(n_simulations - pbar.n)
                            if set_prog is not None:
                                set_prog(int(n_simulations + set_prog_init))
                        break
                    else:
                        if set_prog is not None:
                            set_prog(int(q.qsize() + set_prog_init))
                        if q.qsize() - pbar.n > 0:
                            pbar.update(q.qsize() - pbar.n)
                        time.sleep(.2)
            mcs_out = jobs.get()
            time.sleep(0.1)

        # clean and convert results to dataframe and return
        df_mcs_out = pd.DataFrame(mcs_out)
        df_mcs_out.sort_values("solver_time_equivalence_solved", inplace=True)  # sort base on time equivalence
        return df_mcs_out

    @staticmethod
    def read_spreadsheet_input(fp: str):
        if fp.endswith(".xlsx"):
            df_input = pd.read_excel(fp, index_col=0, header=None, engine='openpyxl')
        elif fp.endswith(".xls"):
            df_input = pd.read_excel(fp, index_col=0, header=None)
        elif fp.endswith(".csv"):
            df_input = pd.read_csv(fp, index_col=0, header=None)
        else:
            raise ValueError(f"Unknown input file format, {os.path.basename(fp)}")

        # assign case_name as column header
        df_input.columns = df_input.loc['case_name'].values

        if len(set((df_input.columns))) != len(df_input.columns):
            raise ValueError(f'case_name not unique')

        dict_input = df_input.to_dict(orient='dict')
        for k in dict_input.keys():
            if 'case_name' not in tuple(dict_input[k].keys()):
                dict_input[k]['case_name'] = k

        return dict_input
