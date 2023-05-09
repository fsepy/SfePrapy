import os

from .calc import teq_main
from .inputs import EXAMPLE_INPUT
from ..mcs0 import MCS0, MCS0Single


class MCS2Single(MCS0Single):
    INPUT_KEYS = (
        'index', 'beam_cross_section_area', 'beam_position_vertical', 'beam_position_horizontal_ratio', 'beam_rho',
        'fire_time_duration', 'fire_time_step', 'fire_combustion_efficiency', 'fire_gamma_fi_q', 'fire_hrr_density',
        'fire_load_density', 'fire_mode', 'fire_nft_limit', 'fire_spread_speed', 'fire_t_alpha', 'fire_tlim',
        'protection_c', 'protection_k', 'protection_protected_perimeter', 'protection_rho', 'room_height',
        'room_wall_thermal_inertia', 'room_floor_area', 'room_breadth_depth_ratio', 'solver_temperature_goal',
        'solver_max_iter', 'solver_thickness_lbound', 'solver_thickness_ubound', 'solver_tol', 'window_open_fraction',
        'window_open_fraction_permanent', 'window_height_room_height_ratio', 'window_area_floor_ratio', 'phi_teq',
        'timber_charring_rate', 'timber_charred_depth', 'timber_hc', 'timber_density', 'timber_exposed_area',
        'timber_depth', 'timber_solver_tol', 'timber_solver_ilim', 'occupancy_type', 'car_cluster_size',
    )
    OUTPUT_KEYS = (
        'index', 'beam_position_horizontal', 'fire_combustion_efficiency', 'fire_hrr_density', 'fire_nft_limit',
        'fire_spread_speed', 'window_open_fraction', 'fire_load_density', 'fire_type', 't1', 't2', 't3',
        'solver_steel_temperature_solved', 'solver_time_critical_temp_solved', 'solver_protection_thickness',
        'solver_iter_count', 'solver_time_equivalence_solved', 'timber_charring_rate', 'timber_exposed_duration',
        'timber_solver_iter_count', 'timber_fire_load', 'timber_charred_depth', 'timber_charred_mass',
        'timber_charred_volume',

        'room_depth', 'room_breadth', 'window_height', 'window_width', 'beam_position_vertical',
    )

    @staticmethod
    def worker(args) -> tuple:
        return teq_main(*args)

    @property
    def input_keys(self) -> tuple:
        return MCS2Single.INPUT_KEYS

    @property
    def output_keys(self) -> tuple:
        return MCS2Single.OUTPUT_KEYS


class MCS2(MCS0):
    @property
    def new_mcs_case(self):
        return MCS2Single


def cli_main(fp_mcs_in: str, n_threads: int = 1):
    fp_mcs_in = os.path.realpath(fp_mcs_in)

    mcs = MCS2()
    mcs.inputs = fp_mcs_in
    mcs.n_threads = n_threads
    mcs.run()
