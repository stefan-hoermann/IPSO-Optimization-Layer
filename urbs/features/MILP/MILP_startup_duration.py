import pyomo.core as pyomo


def MILP_startup_duration(m):
    ##### INPUT #####
    # run[1/0](t) does not have to be accounted for here since it is already implemented in e_pro_in_no_start
    # e_pro_in(t) = e_pro_in_calc_help(t) + startup[1/0](t) * startup_cost
    # e_pro_in_calc_help(t)  - e_pro_in_no_start_up(t) * (tm - t_startup)/tm <= (1 - startup[1/0](t)) * e_in_max
    # e_pro_in_calc_help(t)  - e_pro_in_no_start_up(t) * (tm - t_startup)/tm >= - (1 - startup[1/0](t)) * e_in_max
    # e_pro_in_calc_help(t)  - e_pro_in_no_start_up(t) <= startup[1/0](t) * e_in_max
    # e_pro_in_calc_help(t)  - e_pro_in_no_start_up(t) >= - startup[1/0](t) * e_in_max
    # with
    # e_pro_in_no_start_up(t) = offset(t) + slope * tau_pro(t)
    # R is not required in the e_in_max, it does not make a difference

    m.del_component(m.def_partial_process_input)
    m.del_component(m.def_partial_process_input_index)
    m.e_pro_in_no_start_up = pyomo.Var(
        m.t, m.pro_partial_input_tuples,
        within=pyomo.NonNegativeReals,
        doc='Energy input if there is no startup.')
    m.def_partial_process_input_MILP_no_start = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_MILP_no_start_rule,
        doc='e_pro_in_no_start(t) = offset + slope * tau_pro(t)')

    m.e_pro_in_calc_help = pyomo.Var(
        m.t, m.pro_partial_input_tuples,
        within=pyomo.NonNegativeReals,
        doc='Energy input calculation help.')
    m.def_partial_process_input = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_rule,
        doc='e_pro_in = e_pro_in_calc_help + startup[1/0] * startup_cost ')

    m.def_partial_process_input_MILP_A = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_MILP_rule_A,
        doc='less input power during start-up rule A')
    m.def_partial_process_input_MILP_B = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_MILP_rule_B,
        doc='less input power during start-up rule B')
    m.def_partial_process_input_MILP_C = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_MILP_rule_C,
        doc='less input power during start-up rule C')
    m.def_partial_process_input_MILP_D = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_MILP_rule_D,
        doc='less input power during start-up rule D')

    ##### OUTPUT #####
    # run[1/0](t) does not have to be accounted for here since it is already implemented in e_pro_out_no_start
    # e_pro_out - e_pro_out_no_start(t) * (tm - t_startup)/tm <= (1 - startup[1/0](t)) * e_out_max
    # e_pro_out - e_pro_out_no_start(t) * (tm - t_startup)/tm >= - (1 - startup[1/0](t)) * e_out_max
    # e_pro_out - e_pro_out_no_start(t) <= startup[1/0](t) * e_out_max
    # e_pro_out - e_pro_out_no_start(t) >= - startup[1/0](t) * e_out_max

    m.del_component(m.def_partial_process_output)
    m.e_pro_out_no_start_up = pyomo.Var(
        m.t, (m.pro_partial_output_tuples -
              (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        within=pyomo.NonNegativeReals,
        doc='Energy output if there is no startup.')
    m.pro_out_help_var = pyomo.Var(
        m.t, (m.pro_partial_output_tuples -
              (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        within=pyomo.NonNegativeReals,
        doc='Help variable required to ensure less power during startups.')

    m.def_partial_process_output_MILP_no_start = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MILP_no_start_rule,
        doc='e_pro_out_no_start(t) = offset + slope * tau_pro(t)')
    m.def_partial_process_output_MILP_A = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MILP_rule_A,
        doc='less output power during start-up rule A')
    m.def_partial_process_output_MILP_B = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MILP_rule_B,
        doc='less output power during start-up rule B')
    m.def_partial_process_output_MILP_C = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MILP_rule_C,
        doc='less output power during start-up rule C')
    m.def_partial_process_output_MILP_D = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MILP_rule_D,
        doc='less output power during start-up rule D')
    return m


def def_partial_process_input_MILP_no_start_rule(m, tm, stf, sit, pro, coin):
    # e_pro_in_no_start_up(t) = offset(t) + slope * tau_pro(t)
    return m.e_pro_in_no_start_up[tm, stf, sit, pro, coin] == \
           m.dt * m.pro_p_in_offset[tm, stf, sit, pro, coin] + \
           m.pro_p_in_slope[(stf, sit, pro, coin)] * m.tau_pro[tm, stf, sit, pro]


def def_partial_process_input_rule(m, tm, stf, sit, pro, coin):
    # e_pro_in(t) = e_pro_in_calc_help(t) + startup_costs * startup[1/0](t)
    return m.e_pro_in[tm, stf, sit, pro, coin] == m.e_pro_in_calc_help[tm, stf, sit, pro, coin] \
           + m.dt * m.pro_p_startup[tm, stf, sit, pro, coin] * m.pro_mode_startup[tm, stf, sit, pro]


def def_partial_process_input_MILP_rule_A(m, tm, stf, sit, pro, coin):
    # Rule A: e_pro_in_calc_help(t) - e_pro_in_no_start(t) * (tm - t_startup)/tm  <= (1 - startup[1/0](t)) * e_in_max
    return m.e_pro_in_calc_help[tm, stf, sit, pro, coin] - m.e_pro_in_no_start_up[tm, stf, sit, pro, coin] * \
           ((m.dt - m.process_dict['start-up-duration'][(stf, sit, pro)]) / m.dt) \
           <= (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def def_partial_process_input_MILP_rule_B(m, tm, stf, sit, pro, coin):
    # Rule B: e_pro_in_calc_help(t) - e_pro_in_no_start(t) * (tm - t_startup)/tm  >= -(1 - startup[1/0](t)) * e_in_max
    return m.e_pro_in_calc_help[tm, stf, sit, pro, coin] - m.e_pro_in_no_start_up[tm, stf, sit, pro, coin] * \
           ((m.dt - m.process_dict['start-up-duration'][(stf, sit, pro)]) / m.dt) \
           >= - (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def def_partial_process_input_MILP_rule_C(m, tm, stf, sit, pro, coin):
    # Rule C: e_pro_in_calc_help(t) - e_pro_in_no_start(t) <= startup[1/0](t) * e_in_max
    return m.e_pro_in_calc_help[tm, stf, sit, pro, coin] - m.e_pro_in_no_start_up[tm, stf, sit, pro, coin] \
           <= m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def def_partial_process_input_MILP_rule_D(m, tm, stf, sit, pro, coin):
    # Rule C: e_pro_in_calc_help(t) - e_pro_in_no_start(t) >= - startup[1/0](t) * e_in_max
    return m.e_pro_in_calc_help[tm, stf, sit, pro, coin] - m.e_pro_in_no_start_up[tm, stf, sit, pro, coin] \
           >= - m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def def_partial_process_output_MILP_no_start_rule(m, tm, stf, sit, pro, coo):
    # e_pro_out_no_start(t) = offset + slope * tau_pro(t)
    return m.e_pro_out_no_start_up[tm, stf, sit, pro, coo] == \
           m.dt * m.pro_p_out_offset[tm, stf, sit, pro, coo] + \
           m.pro_p_out_slope[(stf, sit, pro, coo)] * m.tau_pro[tm, stf, sit, pro]


def def_partial_process_output_MILP_rule_A(m, tm, stf, sit, pro, coo):
    # Rule A: e_pro_out(t) - e_out_no_start(t) <= (1 - startup[1/0](t)) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.e_pro_out_no_start_up[tm, stf, sit, pro, coo] * \
           ((m.dt - m.process_dict['start-up-duration'][(stf, sit, pro)]) / m.dt) \
           <= (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def def_partial_process_output_MILP_rule_B(m, tm, stf, sit, pro, coo):
    # Rule B: e_pro_out(t) - e_out_start(t) >= -(1 - startup[1/0](t)) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.e_pro_out_no_start_up[tm, stf, sit, pro, coo] * \
           ((m.dt - m.process_dict['start-up-duration'][(stf, sit, pro)]) / m.dt) \
           >= - (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def def_partial_process_output_MILP_rule_C(m, tm, stf, sit, pro, coo):
    # Rule C: e_pro_out - e_pro_out_no_start(t) <= startup[1/0](t) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.e_pro_out_no_start_up[tm, stf, sit, pro, coo] \
           <= m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt


def def_partial_process_output_MILP_rule_D(m, tm, stf, sit, pro, coo):
    # Rule C: e_pro_out - e_pro_out_no_start(t) >= - startup[1/0](t) * e_out_max
    return m.e_pro_out[tm, stf, sit, pro, coo] - m.e_pro_out_no_start_up[tm, stf, sit, pro, coo] \
           >= - m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt
