import pyomo.core as pyomo
import pandas as pd


def MILP_calculate_startup_input_output(m):
    # e_pro_out = e_pro_out_no_start(t) * (1 - run[1/0](t)) * (1-  startup[1/0](t) * (1 - (tm - t_startup)/tm ))
    #
    # Linearizing Rules:
    # e_out_start(t) =  e_pro_out_no_start(t) * (tm - t_start)/tm
    # e_out_max = cap_up * tm * R       -> R is not really required and thus omitted for better overview
    # Rule 1: e_pro_out(t) - e_out_start(t) <= (1 - startup[1/0](t)) * e_out_max
    # Rule 2: e_pro_out(t) - e_out_start(t) >= -(1 - startup[1/0](t)) * e_out_max
    # Rule 3: e_pro_out(t) - e_pro_out_no_start(t) <= (1 - run[1/0](t)) * e_out_max
    # Rule 4: e_pro_out(t) - e_help >= -(1 - run[1/0](t)) * e_out_max
    #       e_help = e_pro_out_no_start(t) * (1 - startup[1/0](t))      linearized:
    #       Rule 4.1: e_help - e_pro_out_no_start(t) <= startup[1/0](t) * e_out_max
    #       Rule 4.2: e_help - e_pro_out_no_start(t) >= - startup[1/0](t) * e_out_max
    #       Rule 4.3: e_help <= (1 - startup[1/0](t)) * e_out_max
    #       Rule 4.4: e_help >= -(1 - startup[1/0](t)) * e_out_max
    # Rule 5: e_pro_out(t) <= run[1/0](t) * e_out_max
    # Rule 6: e_pro_out(t) >= - run[1/0](t) * e_out_max

    m.del_component(m.def_partial_process_output)
    m.pro_out_no_start_up = pyomo.Var(
        m.t, m.pro_output_tuples,
        within=pyomo.NonNegativeReals,
        doc='Energy output if there is no startup.')
    # TODO: change generation of variables so it is not generated for all output tuples but just for the partial ones
    m.pro_out_help_var = pyomo.Var(
        m.t, m.pro_output_tuples,
        within=pyomo.NonNegativeReals,
        doc='Help variable required to ensure less power during startups.')

    m.def_partial_process_output_MILP_no_start = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MILP_no_start_rule,
        doc='e_pro_out_no_start(t) = offset + slope * tau_pro(t)')
    m.def_partial_process_output_MILP_1 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_1,
        doc='less power during start-up rule 1')

    m.def_partial_process_output_MILP_2 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_2,
        doc='less power during start-up rule 2')
    m.def_partial_process_output_MILP_3 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_3,
        doc='less power during start-up rule 3')
    m.def_partial_process_output_MILP_4 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_4,
        doc='less power during start-up rule 4')
    m.def_partial_process_output_MILP_4_1 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_4_1,
        doc='less power during start-up rule 4_1')
    m.def_partial_process_output_MILP_4_2 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_4_2,
        doc='less power during start-up rule 4_2')
    m.def_partial_process_output_MILP_4_3 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_4_3,
        doc='less power during start-up rule 4_3')
    m.def_partial_process_output_MILP_4_4 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_4_4,
        doc='less power during start-up rule 4_4')
    m.def_partial_process_output_MILP_5 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_5,
        doc='less power during start-up rule 5')
    m.def_partial_process_output_MILP_6 = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=res_partial_process_output_MILP_rule_6,
        doc='less power during start-up rule 6')



    # m.def_partial_process_input = pyomo.Constraint(
    #     m.tm, m.pro_partial_input_tuples,
    #     rule=def_partial_process_input_MILP_rule,
    #     doc='e_pro_in = offset + slope * tau_pro + startup_costs'
    #         'slope = (R -  min_fraction * r) / (1 - min_fraction); offset = R - slope')


    return m



def def_partial_process_output_MILP_no_start_rule(m, tm, stf, sit, pro, coo):
    # e_pro_out_no_start(t) = offset + slope * tau_pro(t)
    return m.pro_out_no_start_up[tm, stf, sit, pro, coo] == \
           m.dt * m.pro_p_out_offset[tm, stf, sit, pro, coo] + \
           m.pro_p_out_slope[(stf, sit, pro, coo)] * m.tau_pro[tm, stf, sit, pro]


def res_partial_process_output_MILP_rule_1(m, tm, stf, sit, pro, coo):
    # Rule 1: e_pro_out(t) - e_out_start(t) <= (1 - startup[1/0](t)) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.pro_out_no_start_up[tm, stf, sit, pro, coo] * \
           ((m.dt - m.process_dict['start-up-duration'][(stf, sit, pro)]) / m.dt)\
           <= (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_2(m, tm, stf, sit, pro, coo):
    # Rule 2: e_pro_out(t) - e_out_start(t) >= -(1 - startup[1/0](t)) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.pro_out_no_start_up[tm, stf, sit, pro, coo] * \
           ((m.dt - m.process_dict['start-up-duration'][(stf, sit, pro)]) / m.dt)\
           >= - (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_3(m, tm, stf, sit, pro, coo):
    # Rule 3: e_pro_out(t) - e_pro_out_no_start(t) <= (1 - run[1/0](t)) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.pro_out_no_start_up[tm, stf, sit, pro, coo] \
           <= (1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt

def res_partial_process_output_MILP_rule_4(m, tm, stf, sit, pro, coo):
    # Rule 4: e_pro_out(t) - e_help >= -(1 - run[1/0](t)) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.pro_out_help_var[tm, stf, sit, pro, coo] \
           >= - (1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_4_1(m, tm, stf, sit, pro, coo):
    # Rule 4.1: e_help - e_pro_out_no_start(t) <= startup[1/0](t) * e_out_max
    return m.pro_out_help_var[tm, stf, sit, pro, coo] - m.pro_out_no_start_up[tm, stf, sit, pro, coo] \
           <= m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_4_2(m, tm, stf, sit, pro, coo):
    # Rule 4.2: e_help - e_pro_out_no_start(t) >= - startup[1/0](t) * e_out_max
    return m.pro_out_help_var[tm, stf, sit, pro, coo] - m.pro_out_no_start_up[tm, stf, sit, pro, coo] \
           >= - m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_4_3(m, tm, stf, sit, pro, coo):
    # Rule 4.3: e_help <= (1 - startup[1/0](t)) * e_out_max
    return m.pro_out_help_var[tm, stf, sit, pro, coo]\
           <= (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_4_4(m, tm, stf, sit, pro, coo):
    # Rule 4.4: e_help >= -(1 - startup[1/0](t)) * e_out_max
    return m.pro_out_help_var[tm, stf, sit, pro, coo]\
           >= - (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_5(m, tm, stf, sit, pro, coo):
    # Rule 5: e_pro_out(t) <= run[1/0](t) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo]\
           <= m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def res_partial_process_output_MILP_rule_6(m, tm, stf, sit, pro, coo):
    # Rule 6: e_pro_out(t) >= - run[1/0](t) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo]\
           >= - m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt





















