import pyomo.core as pyomo
import pandas as pd

# Ensures a minimum consecutive operation time
def MILP_min_operation_time(m):
    # validation: ther must be a min-ocon-op time if pre-active timesteps is given min_consecutive_op_time_dict
    m.pro_min_con_duration_tuples = pyomo.Set(
        within=m.stf * m.sit * m.pro,
        initialize=[(stf, site, process)
                    for (stf, site, process) in m.pro_partial_tuples
                    for (st, si, pro) in tuple(m.min_consecutive_op_time_dict.keys())
                    if process == pro and si == site],
        doc='Processes with min consecutive operation time,'
            'e.g. (2020,Hormann,CHP1)')

    m.pro_out_last_n_timesteps = pyomo.Var(
        m.t, m.pro_min_con_duration_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process inactive/not in operation in one of the last n timesteps.')

    m.res_pro_min_cons_op_time_1 = pyomo.Constraint(
        m.tm, m.pro_min_con_duration_tuples,
        rule=res_pro_min_cons_op_time_rule_1,
        doc='n * out_last_n_timesteps[1/0] >= (1 - run(t-1)) + (1 - run(t-i)) + … + (1 - run(t-n))')

    m.res_pro_min_cons_op_time_2 = pyomo.Constraint(
        m.tm, m.pro_min_con_duration_tuples,
        rule=res_pro_min_cons_op_time_rule_2,
        doc='run(t) >= out_last_n_timesteps[1/0] - (1 - run(t-1))')

    m.res_pro_min_cons_op_time_3 = pyomo.Constraint(
        m.pro_min_con_duration_tuples,
        rule=res_pro_min_cons_op_time_rule_3,
        doc='run(0) == 0 if not active before')

    # m.res_pro_min_cons_op_time_test_rule = pyomo.Constraint(
    #     m.pro_min_con_duration_tuples,
    #     rule=res_pro_min_cons_test,
    #     doc='run(0) == 0 if not active before')
    return m

# def res_pro_min_cons_test(m, stf, sit, pro):
#     if m.process_dict['min-con-op-time'][(stf, sit, pro)] > 0:
#         return m.pro_mode_run[15, stf, sit, pro] == 1
#     else:
#         return pyomo.Constraint.Skip


def res_pro_min_cons_op_time_rule_1(m, tm, stf, sit, pro):
    # tm_relative is required if the timestep-offset is not 0
    tm_relative = tm - m.timesteps[0]
    # Constraint is skipped if there is no or a negative min-con-op-time
    if m.process_dict['min-con-op-time'][(stf, sit, pro)] <= 0:
        return pyomo.Constraint.Skip
    # If the process is already active at the start, it has to remain active for min-con-op-time - pre-active-timesteps
    # -> NO optimization
    # if not, the initial state is set to be off (rule 3).
    if m.process_dict['pre-active-timesteps'][(stf, sit, pro)] > 0 and\
            tm_relative <= m.process_dict['min-con-op-time'][(stf, sit, pro)] - m.process_dict['pre-active-timesteps'][(stf, sit, pro)]:
        return m.pro_mode_run[tm, stf, sit, pro] == 1

    # After the starting fored-activity (meaning min-con-op-time - pre-active-timesteps < t)
    # Or if the process is not active at the start, the optimization begins right away:
    # n * out_last_n_timesteps[1/0] >= (1 - run(t-1)) + (1 - run(t-i)) + … + (1 - run(t-n))
    # Hereby n is the amount of timesteps the process has to stay active.
    if tm_relative <= m.process_dict['min-con-op-time'][(stf, sit, pro)]:
        return m.pro_out_last_n_timesteps[tm, stf, sit, pro] * tm_relative >=\
               sum((1 - m.pro_mode_run[tm - i, stf, sit, pro]) for i in range(1, tm_relative+1))

    else:
        return m.pro_out_last_n_timesteps[tm, stf, sit, pro] * m.process_dict['min-con-op-time'][(stf, sit, pro)] >= \
               sum((1 - m.pro_mode_run[tm - i, stf, sit, pro])
                   for i in range(1, m.process_dict['min-con-op-time'][(stf, sit, pro)] + 1))


def res_pro_min_cons_op_time_rule_2(m, tm, stf, sit, pro):
    # run(t) >= out_last_n_timesteps[1/0] - (1 - run(t-1))
    if m.process_dict['min-con-op-time'][(stf, sit, pro)] <= 0:
        return pyomo.Constraint.Skip

    else:
        return m.pro_mode_run[tm, stf, sit, pro] >= m.pro_out_last_n_timesteps[tm, stf, sit, pro] - \
               (1 - m.pro_mode_run[tm - 1, stf, sit, pro])


def res_pro_min_cons_op_time_rule_3(m, stf, sit, pro):
    # initializes pro_mode_run to 0 if the process is not active before
    if m.process_dict['min-con-op-time'][(stf, sit, pro)] > 0 and m.process_dict['pre-active-timesteps'][(stf, sit, pro)] == 0:
        return m.pro_mode_run[0, stf, sit, pro] == 0
    else:
        return pyomo.Constraint.Skip