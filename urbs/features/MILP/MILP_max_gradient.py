import pyomo.core as pyomo


def MILP_max_gradient(m):
    m.pro_mode_turnoff = pyomo.Var(
        m.tm, m.pro_partial_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process is turning off')
    m.del_component(m.res_process_maxgrad_lower)
    m.del_component(m.res_process_maxgrad_lower_index)
    m.del_component(m.res_process_maxgrad_upper)
    m.del_component(m.res_process_maxgrad_upper_index)
    # Pyomo does not support partial deletion, thus the gradient constraint have to be reformulated for processes with
    # max gradient but without partload behaviour
    m.res_process_maxgrad_lower = pyomo.Constraint(
        m.tm, m.pro_maxgrad_tuples - m.pro_partial_tuples,
        rule=res_process_maxgrad_lower_rule,
        doc='throughput may not decrease faster than maximal gradient')
    m.res_process_maxgrad_upper = pyomo.Constraint(
        m.tm, m.pro_maxgrad_tuples - m.pro_partial_tuples,
        rule=res_process_maxgrad_upper_rule,
        doc='throughput may not increase faster than maximal gradient')

    m.res_process_maxgrad_start_up = pyomo.Constraint(
        m.tm, m.pro_partial_tuples & m.pro_maxgrad_tuples,
        rule=res_process_maxgrad_start_up_rule,
        doc='max gradient exception for startup')
    m.res_process_maxgrad_turn_off = pyomo.Constraint(
        m.tm, m.pro_partial_tuples & m.pro_maxgrad_tuples,
        rule=res_process_maxgrad_turn_off_rule,
        doc='max gradient exception for turnoff')
    # tau_pro(t) - (tau_pro(t-1) + cap_pro * max_grad * dt) <= startup[1/0](t) * cap_pro * dt
    # tau_pro(t) - (tau_pro(t-1) - cap_pro * max_grad * dt) >= - turnoff[1/0](t) * cap_pro * dt
    return m


def def_pro_mode_turnoff_rule(m, tm, stf, sit, pro):
    # turnoff == run[t-1] * (1 - run[t])
    return m.pro_mode_startup[tm, stf, sit, pro] == \
           m.pro_mode_run[tm - 1, stf, sit, pro] * (1 - m.pro_mode_run[tm, stf, sit, pro])


def res_process_maxgrad_start_up_rule(m, tm, stf, sit, pro):
    # tau_pro(t) - (tau_pro(t-1) + cap_pro * max_grad * dt) <= startup[1/0](t) * cap_pro * dt
    return m.tau_pro[tm, stf, sit, pro] - (m.tau_pro[tm - 1, stf, sit, pro] + m.cap_pro[stf, sit, pro] *
                                           m.process_dict['max-grad'][(stf, sit, pro)] * m.dt) \
           <= m.pro_mode_startup[tm, stf, sit, pro] * m.cap_pro[stf, sit, pro] * m.dt


def res_process_maxgrad_turn_off_rule(m, tm, stf, sit, pro):
    # tau_pro(t) - (tau_pro(t-1) - cap_pro * max_grad * dt) >= - turnoff[1/0](t) * cap_pro * dt
    return m.tau_pro[tm, stf, sit, pro] - (m.tau_pro[tm - 1, stf, sit, pro] - m.cap_pro[stf, sit, pro] *
                                           m.process_dict['max-grad'][(stf, sit, pro)] * m.dt) \
           >= - m.pro_mode_turnoff[tm, stf, sit, pro] * m.cap_pro[stf, sit, pro] * m.dt

def res_process_maxgrad_lower_rule(m, t, stf, sit, pro):
    return (m.tau_pro[t - 1, stf, sit, pro] -
            m.cap_pro[stf, sit, pro] *
            m.process_dict['max-grad'][(stf, sit, pro)] * m.dt <=
            m.tau_pro[t, stf, sit, pro])


def res_process_maxgrad_upper_rule(m, t, stf, sit, pro):
    return (m.tau_pro[t - 1, stf, sit, pro] +
            m.cap_pro[stf, sit, pro] *
            m.process_dict['max-grad'][(stf, sit, pro)] * m.dt >=
            m.tau_pro[t, stf, sit, pro])