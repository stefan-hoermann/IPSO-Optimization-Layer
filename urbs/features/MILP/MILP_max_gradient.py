import pyomo.core as pyomo


def MILP_max_gradient(m):
    m.pro_mode_turnoff = pyomo.Var(
        m.tm, m.pro_partial_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process is turning off')
    # Logic table for turn off:
    # run[t] X run[t-1] X          X  rule1  X  rule2  X  rule3  X sum_rules
    #   0    X    0     X turnoff X   >=0   X   <=1   X  <=0    X    =0
    #   0    X    1     X turnoff X   >=1   X   <=1   X  <=1    X    =1
    #   1    X    0     X turnoff X   >=-1  X   <=0   X  <=0    X    =0
    #   1    X    1     X turnoff X   >=0   X   <=0   X  <=1    X    =0
    m.pro_mode_turnoff1 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=pro_mode_turnoff_rule1,
        doc='turnoff >= run[t-1] - run[t]')

    m.pro_mode_turnoff2 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=pro_mode_turnoff_rule2,
        doc='turnoff <= 1 - run[t]')

    m.pro_mode_turnoff3 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=pro_mode_turnoff_rule3,
        doc='turnoff <= run [t-1]')
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

    # If min_fraction > max_grad, the gradient condition has to be set inactive because the process could not start up
    # otherwise. If min_fraction < max_grad, the basic lower and upper gradient restrictions stay intact for both start
    # and turnoff. This persists even in case of startup duration, since the startup-duration restriction is not based
    # on the throughput but the inputs and outputs directly.
    # t_startup does not have to be regarded since t_startup defines the time until min power
    # tau(t-1) +  cap_pro(t) * max_grad * dt  >= tau(t) * (1 - startup(t))
    # -> linearized: tau_pro(t) - (tau_pro(t-1) + cap_pro * max_grad * dt) <= startup[1/0](t) * cap_up * dt
    # If min_fraction > max_grad, tau_pro = min_power in the startup timestep
    # startup(t) * cap_pro(t) * min_fract  * dt <= tau_pro(t)
    # -> linearized: tau_pro(t) - cap_pro(t) * min_fract  * dt <= (1 - startup(t)) * cap_up * dt
    # cap_pro(t) * min_fract  * dt >= startup(t) *  tau_pro(t)
    # -> linearized: tau_pro(t) - cap_pro(t) * min_fract  * dt >= - (1 - startup(t)) * cap_up * dt

    m.res_process_maxgrad_start_up_1= pyomo.Constraint(
        m.tm, m.pro_partial_tuples & m.pro_maxgrad_tuples,
        rule=res_process_maxgrad_start_up_rule_1,
        doc='max gradient exception for startup')
    m.res_process_maxgrad_start_up_2 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples & m.pro_maxgrad_tuples,
        rule=res_process_maxgrad_start_up_rule_2,
        doc='max gradient exception for startup')
    m.res_process_maxgrad_start_up_3 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples & m.pro_maxgrad_tuples,
        rule=res_process_maxgrad_start_up_rule_3,
        doc='max gradient exception for startup')
    # Similarily, if min_fraction > max_grad, the gradient condition has to be set inactive for the turnoff
    # (tau(t-1) -  cap_pro(t) * max_grad * dt) * (1 - turnoff(t))  <= tau(t)
    # -> linearized: tau_pro(t) - (tau_pro(t-1) - cap_pro * max_grad * dt) >= - turnoff[1/0](t) * cap_up * dt
    m.res_process_maxgrad_turn_off = pyomo.Constraint(
        m.tm, m.pro_partial_tuples & m.pro_maxgrad_tuples,
        rule=res_process_maxgrad_turn_off_rule,
        doc='max gradient exception for turnoff')

    return m

def pro_mode_turnoff_rule1(m, tm, stf, sit, pro):
    # turnoff >= run[t-1] - run[t]
    return m.pro_mode_turnoff[tm, stf, sit, pro] >= \
           m.pro_mode_run[tm - 1, stf, sit, pro] - m.pro_mode_run[tm, stf, sit, pro]


def pro_mode_turnoff_rule2(m, tm, stf, sit, pro):
    # turnoff <= 1 - run[t]
    return m.pro_mode_turnoff[tm, stf, sit, pro] <= 1 - m.pro_mode_run[tm, stf, sit, pro]


def pro_mode_turnoff_rule3(m, tm, stf, sit, pro):
    # turnoff <= run[t-1]
    return m.pro_mode_startup[tm, stf, sit, pro] <= m.pro_mode_run[tm - 1, stf, sit, pro]

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


def res_process_maxgrad_start_up_rule_1(m, tm, stf, sit, pro):
    # tau_pro(t) - (tau_pro(t-1) + cap_pro * max_grad * dt) <= startup[1/0](t) * cap_up * dt
    if m.process_dict['min-fraction'][(stf, sit, pro)] >= m.process_dict['max-grad'][(stf, sit, pro)]:
        return m.tau_pro[tm, stf, sit, pro] - (m.tau_pro[tm - 1, stf, sit, pro] + m.cap_pro[stf, sit, pro] *
                                               m.process_dict['max-grad'][(stf, sit, pro)] * m.dt) \
               <= m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt
    else:
        return res_process_maxgrad_upper_rule()

def res_process_maxgrad_start_up_rule_2(m, tm, stf, sit, pro):
    if m.process_dict['min-fraction'][(stf, sit, pro)] >= m.process_dict['max-grad'][(stf, sit, pro)]:
        # tau_pro(t) - cap_pro(t) * min_fract  * dt <= (1 - startup(t)) * cap_up * dt
        return (m.tau_pro[tm, stf, sit, pro] - m.cap_pro[stf, sit, pro] * \
        m.process_dict['min-fraction'][(stf, sit, pro)] * m.dt <= (1 - m.pro_mode_startup[tm, stf, sit, pro]) *
                m.process_dict['cap-up'][(stf, sit, pro)])
    else:
        return pyomo.Constraint.Skip

def res_process_maxgrad_start_up_rule_3(m, tm, stf, sit, pro):
    if m.process_dict['min-fraction'][(stf, sit, pro)] >= m.process_dict['max-grad'][(stf, sit, pro)]:
        # tau_pro(t) - cap_pro(t) * min_fract * dt >= - (1 - startup(t)) * cap_up * dt
        return (m.tau_pro[tm, stf, sit, pro] - m.cap_pro[stf, sit, pro] * \
                m.process_dict['min-fraction'][(stf, sit, pro)] * m.dt >= -(1 - m.pro_mode_startup[tm, stf, sit, pro]) *
                m.process_dict['cap-up'][(stf, sit, pro)] * m.dt)
    else:
        return pyomo.Constraint.Skip

def res_process_maxgrad_turn_off_rule(m, tm, stf, sit, pro):
    if m.process_dict['min-fraction'][(stf, sit, pro)] >= m.process_dict['max-grad'][(stf, sit, pro)]:
        # tau_pro(t) - (tau_pro(t-1) - cap_pro * max_grad * dt) >= - turnoff[1/0](t) * cap_up * dt
        return m.tau_pro[tm, stf, sit, pro] - (m.tau_pro[tm - 1, stf, sit, pro] - m.cap_pro[stf, sit, pro] *
                                               m.process_dict['max-grad'][(stf, sit, pro)] * m.dt) \
               >= - m.pro_mode_turnoff[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt

    else:
        return res_process_maxgrad_lower_rule
