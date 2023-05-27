import pyomo.core as pyomo
import pandas as pd



def MILP_calc_offset_slope(m):
    m.pro_p_in_slope = pd.Series(index=m.pro_partial_input_tuples.value_list)
    m.pro_p_in_offset_spec = pd.Series(index=m.pro_partial_input_tuples.value_list)
    for idx in m.pro_p_in_slope.index:
        # input ratio at maximum operation point
        R = m.r_in_dict[(idx[0],)+idx[2:4]]
        # input ratio at lowest operation point
        r = m.r_in_min_fraction_dict[(idx[0],)+idx[2:4]]
        min_fraction = m.process_dict['min-fraction'][idx[0:3]]
        m.pro_p_in_slope[idx] = (R - min_fraction * r) / (1 - min_fraction)
        m.pro_p_in_offset_spec[idx] = R - m.pro_p_in_slope[idx]
    m.pro_p_out_slope = pd.Series(index=m.pro_partial_output_tuples.value_list)
    m.pro_p_out_offset_spec = pd.Series(index=m.pro_partial_output_tuples.value_list)
    for idx in m.pro_p_out_slope.index:
        # output ratio at maximum operation point
        R = m.r_out_dict[(idx[0],)+idx[2:4]]
        # output ratio at lowest operation point
        r = m.r_out_min_fraction_dict[(idx[0],)+idx[2:4]]
        min_fraction = m.process_dict['min-fraction'][idx[0:3]]
        m.pro_p_out_slope[idx] = (R - min_fraction * r) / (1 - min_fraction)
        m.pro_p_out_offset_spec[idx] = R - m.pro_p_out_slope[idx]
    return m


# calculates the offset: p_offset = offset_spec * cap(t) * run[0/1](t)
# linearization:
# 1. p_offset - (offset_spec*cap) <= (1-run) * cap-max * R -> p_offset <= (offset_spec*cap) if run=1
# 2. p_offset - (offset_spec*cap) >= -(1-run) * cap-max * R -> p_offset >= (offset_spec*cap) if run=1
# 3. p_offset <= run * cap_max * R
# 4. p_offset >= -run * cap_max * R
def MILP_pro_p_offset(m):
    # in:
    m.pro_p_in_offset = pyomo.Var(
        m.tm, m.pro_partial_input_tuples,
        within=pyomo.Reals,
        doc='offset for calculating process input')

    m.pro_p_in_offset_lt = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_in_offset_lt_rule,
        doc='offset must be (lower) equal to offset_spec*cap , when run = 1'
            'p_offset - (offset_spec*cap) <= (1-run) * cap-max * R -> p_offset <= (offset_spec*cap) if run=1.')

    m.pro_p_in_offset_gt = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_in_offset_gt_rule,
        doc='offset must be (greater) equal to offset_spec*cap , when run = 1'
            'p_offset - (offset_spec*cap) >= -(1-run) * cap-max  * R -> p_offset >= (offset_spec*cap) if run=1')

    m.pro_p_offset_in_ltzero_when_off = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_offset_in_ltzero_when_off_rule,
        doc='p_offset must be (lower) equal to zero when run=0'
            'p_offset <= run * cap_max * R')

    m.pro_p_offset_in_gtzero_when_off = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_offset_in_gtzero_when_off_rule,
        doc='p_offset must be (greater) equal to zero when run=0'
            'p_offset >= -run * cap_max * R')

    # out:
    m.pro_p_out_offset = pyomo.Var(
        m.tm, m.pro_partial_output_tuples,
        within=pyomo.Reals,
        doc='offset for calculating process output')

    m.pro_p_out_offset_lt = pyomo.Constraint(
        m.tm, m.pro_partial_output_tuples,
        rule=pro_p_out_offset_lt_rule,
        doc='offset must be (lower) equal to offset_spec*cap , when run = 1'
            'p_offset - (offset_spec*cap) <= (1-run) * cap-max * R -> p_offset <= (offset_spec*cap) if run=1.')

    m.pro_p_out_offset_gt = pyomo.Constraint(
        m.tm, m.pro_partial_output_tuples,
        rule=pro_p_out_offset_gt_rule,
        doc='offset must be (greater) equal to offset_spec*cap , when run = 1'
            'p_offset - (offset_spec*cap) >= -(1-run) * cap-max  * R -> p_offset >= (offset_spec*cap) if run=1')

    m.pro_p_offset_out_ltzero_when_off = pyomo.Constraint(
        m.tm, m.pro_partial_output_tuples,
        rule=pro_p_offset_out_ltzero_when_off_rule,
        doc='p_offset must be (lower) equal to zero when run=0'
            'p_offset <= run * cap_max * R')

    m.pro_p_offset_out_gtzero_when_off = pyomo.Constraint(
        m.tm, m.pro_partial_output_tuples,
        rule=pro_p_offset_out_gtzero_when_off_rule,
        doc='p_offset must be (greater) equal to zero when run=0'
            'p_offset >= run * cap_max * R')
    return m


def pro_p_in_offset_lt_rule(m, tm, stf, sit, pro, coin):
    # p_offset - (offset_spec*cap) <= (1-run) * cap-max * R
    return m.pro_p_in_offset[tm, stf, sit, pro, coin] - \
           m.pro_p_in_offset_spec[stf, sit, pro, coin] * m.cap_pro[stf, sit, pro] <= \
           (1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.r_in_dict[(stf, pro, coin)]

def pro_p_in_offset_gt_rule(m, tm, stf, sit, pro, coin):
    # p_offset - (offset_spec*cap) >= -(1-run) * cap-max  * R
    return m.pro_p_in_offset[tm, stf, sit, pro, coin] - \
           m.pro_p_in_offset_spec[stf, sit, pro, coin] * m.cap_pro[stf, sit, pro] >= \
           -(1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.r_in_dict[(stf, pro, coin)]

def pro_p_offset_in_ltzero_when_off_rule(m, tm, stf, sit, pro, coin):
    # p_offset <= run * cap_max * R
    return m.pro_p_in_offset[tm, stf, sit, pro, coin] <= \
           m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)]

def pro_p_offset_in_gtzero_when_off_rule(m, tm, stf, sit, pro, coin):
    # p_offset >= -run * cap_max * R
    return m.pro_p_in_offset[tm, stf, sit, pro, coin] >= \
           -m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)]


def pro_p_out_offset_lt_rule(m, tm, stf, sit, pro, coo):
    # p_offset - (offset_spec*cap) <= (1-run) * cap-max * R
    return m.pro_p_out_offset[tm, stf, sit, pro, coo] - \
           m.pro_p_out_offset_spec[stf, sit, pro, coo] * m.cap_pro[stf, sit, pro] <= \
           (1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.r_out_dict[(stf, pro, coo)]

def pro_p_out_offset_gt_rule(m, tm, stf, sit, pro, coo):
    # p_offset - (offset_spec*cap) >= -(1-run) * cap-max  * R
    return m.pro_p_out_offset[tm, stf, sit, pro, coo] - \
           m.pro_p_out_offset_spec[stf, sit, pro, coo] * m.cap_pro[stf, sit, pro] >= \
           -(1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.r_out_dict[(stf, pro, coo)]

def pro_p_offset_out_ltzero_when_off_rule(m, tm, stf, sit, pro, coo):
    # p_offset <= run * cap_max * R
    return m.pro_p_out_offset[tm, stf, sit, pro, coo] <= \
           m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.r_out_dict[(stf, pro, coo)]

def pro_p_offset_out_gtzero_when_off_rule(m, tm, stf, sit, pro, coo):
    # p_offset >= run * cap_max * R
    return m.pro_p_out_offset[tm, stf, sit, pro, coo] >= \
           -m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.r_out_dict[(stf, pro, coo)]

