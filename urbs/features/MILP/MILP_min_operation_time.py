import pyomo.core as pyomo
import pandas as pd

# Ensures a minimum consecutive operation time
def MILP_min_operation_time(m):
    m.pro_out_last_n_timesteps = pyomo.Var(
        m.t, m.pro_partial_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process inactive/not in operation in one of the last n timesteps.')

    m.res_pro_min_cons_op_time_1 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=res_pro_min_cons_op_time_rule_1,
        doc='n * out_last_n_timesteps[1/0] >= (1 - run(t-1)) + (1 - run(t-i)) + … + (1 - run(t-n))')

    m.res_pro_min_cons_op_time_2 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=res_pro_min_cons_op_time_rule_2,
        doc='run(t) >= out_last_n_timesteps[1/0] - (1 - run(t-1))')

    return m

def res_pro_min_cons_op_time_rule_1(m, tm, stf, sit, pro):
    # n * out_last_n_timesteps[1/0] >= (1 - run(t-1)) + (1 - run(t-i)) + … + (1 - run(t-n))
    # Hereby n is the amount of timesteps the process has to stay active.
    if m.process_dict['min-con-op-time'][(stf, sit, pro)] <= 0 or tm <= 1:
        return pyomo.Constraint.Skip

    if tm <= m.process_dict['min-con-op-time'][(stf, sit, pro)]:
        return m.pro_out_last_n_timesteps[tm, stf, sit, pro] * tm >=\
               sum((1 - m.pro_mode_run[tm - i, stf, sit, pro]) for i in range(1, tm-1))

    else:
        return m.pro_out_last_n_timesteps[tm, stf, sit, pro] * m.process_dict['min-con-op-time'][(stf, sit, pro)] >= \
               sum((1 - m.pro_mode_run[tm - i, stf, sit, pro]) for i in range(1, m.process_dict['min-con-op-time'][(stf, sit, pro)]))



def res_pro_min_cons_op_time_rule_2(m, tm, stf, sit, pro):
    # run(t) >= out_last_n_timesteps[1/0] - (1 - run(t-1))
    if m.process_dict['min-con-op-time'][(stf, sit, pro)] <= 0 or tm <= 1:
        return pyomo.Constraint.Skip

    else:
        return m.pro_mode_run[tm, stf, sit, pro] >= m.pro_out_last_n_timesteps[tm, stf, sit, pro] - \
               (1 - m.pro_mode_run[tm - 1, stf, sit, pro])
