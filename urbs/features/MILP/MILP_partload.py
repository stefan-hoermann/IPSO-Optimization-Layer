from .MILP_startupcosts import MILP_startupcosts
from .MILP_offset_slope import MILP_calc_offset_slope
from .MILP_offset_slope import MILP_pro_p_offset
import pyomo.core as pyomo
import pandas as pd


def MILP_partload(m):
    # Binary Variable if MILP-cap_min is activated
    m.pro_mode_run = pyomo.Var(
        m.t, m.pro_partial_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process in run mode')
    m = MILP_startupcosts(m)
    m.del_component(m.res_throughput_by_capacity_min)
    m.del_component(m.res_throughput_by_capacity_min_index)
    m.res_throughput_by_capacity_min_MILP = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=res_throughput_by_capacity_min_MILP_rule,
        doc='run[0/1] * cap_pro * min-fraction <= tau_pro')

    m.res_process_throughput_by_capacity_MILP = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=res_throughput_by_capacity_max_MILP_rule,
        doc='tau_pro <= run[0/1] * cap-up')

    # Calculate offset and slope for partload behaviour
    m = MILP_calc_offset_slope(m)

    # MILP constraints for offset
    m = MILP_pro_p_offset(m)

    m.del_component(m.def_partial_process_input)
    m.del_component(m.def_partial_process_input_index)
    m.del_component(m.def_partial_process_output)
    m.del_component(m.def_partial_process_output_index)
    m.del_component(m.def_partial_process_output_index_1)
    m.del_component(m.def_partial_process_output_index_1_index_1)
    try:
        m.del_component(m.def_process_partial_timevar_output)
        m.del_component(m.def_process_partial_timevar_output_index)
        m.del_component(m.def_process_partial_timevar_output_index_1)
    except AttributeError:
        pass
    m.def_partial_process_input = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_MILP_rule,
        doc='e_pro_in = offset + slope * tau_pro + startup_costs'
            'slope = (R -  min_fraction * r) / (1 - min_fraction); offset = R - slope')
    m.def_partial_process_output = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
            (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MILP_rule,
        doc='e_pro_out = offset + slope * tau_pro'
            'slope = (R -  min_fraction * r) / (1 - min_fraction); offset = R - slope')
    m.def_process_partial_timevar_output = pyomo.Constraint(
        m.tm, m.pro_partial_output_tuples & m.pro_timevar_output_tuples,
        rule=def_pro_partial_timevar_output_MILP_rule,
        doc='e_pro_out = (offset + slope * tau_pro) * eff_factor'
            'slope = (R -  min_fraction * r) / (1 - min_fraction); offset = R - slope')
    return m



def res_throughput_by_capacity_min_MILP_rule(m, tm, stf, sit, pro):
    # run[0/1] * cap_pro * min - fraction <= tau_pro
    # linearization: tau_pro - cap_pro * min-fraction >= - (1 - run[0/1]) * process.cap-up
    return (m.tau_pro[tm, stf, sit, pro] -
            m.cap_pro[stf, sit, pro] * m.process_dict['min-fraction'][(stf, sit, pro)] * m.dt >=
            - (1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt)


def res_throughput_by_capacity_max_MILP_rule(m, tm, stf, sit, pro):
    # tau_pro <= run[0/1] * cap-up
    return (m.tau_pro[tm, stf, sit, pro] <=
            m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt)



def def_partial_process_input_MILP_rule(m, tm, stf, sit, pro, coin):
    # e_pro_in = offset + slope * tau_pro + startup_costs
    return m.e_pro_in[tm, stf, sit, pro, coin] == \
           m.dt * m.pro_p_in_offset[tm, stf, sit, pro, coin] + \
           m.pro_p_in_slope[(stf, sit, pro, coin)] * m.tau_pro[tm, stf, sit, pro] \
           + m.dt * m.pro_p_startup[tm, stf, sit, pro,coin]


def def_partial_process_output_MILP_rule(m, tm, stf, sit, pro, coo):
    # e_pro_out = offset + slope * tau_pro
    return m.e_pro_out[tm, stf, sit, pro, coo] == \
           m.dt * m.pro_p_out_offset[tm, stf, sit, pro, coo] + \
           m.pro_p_out_slope[(stf, sit, pro, coo)] * m.tau_pro[tm, stf, sit, pro]

def def_pro_partial_timevar_output_MILP_rule(m, tm, stf, sit, pro, coo):
    # e_pro_out = (offset + slope * tau_pro) * eff_factor
    return m.e_pro_out[tm, stf, sit, pro, coo] == \
           (m.dt * m.pro_p_out_offset[tm, stf, sit, pro, coo] +
            m.pro_p_out_slope[(stf, sit, pro, coo)] * m.tau_pro[tm, stf, sit, pro]) * \
           m.eff_factor_dict[(sit, pro)][(stf, tm)]

