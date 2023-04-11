from pyomo.environ import *

# Define the lists and constants
Nodes = [1, 2, 3]  # List of nodes in the heat network
Pipes = ['A', 'B']  # List of pipes in the heat network
c_f = (500 - 200) / 1000  # Constant factor used in power injection calculation
T_Supply = 80  # Supply temperature
T_Return = 50  # Return temperature
TimeSteps = [1]  # List of time steps

# Define the sets and bounds assumptions for the problem
S_n_minus = {1: ['A'], 2: ['B'], 3: []}  # Incoming pipes for each nod
S_n_plus = {1: [], 2: ['A'], 3: []}  # Outgoing pipes for each node            #m_node[3,1] == m_pipe[3,1]
I_n = {1: ['A'], 2: ['B'], 3: ['B']}  # Incidence matrix for nodes and pipes
# Update the mass flow bounds
m_n_bounds = {1: (0, 150), 2: (0, 150), 3: (0, 300)}  # Bounds for mass flow rates at each node
m_p_bounds = {'A': (0, 300), 'B': (0, 300)}  # Bounds for mass flow rates in each pipe

P_H_bounds = {1: (0, 1), 2: (0, 1), 3: (0, 1)}  # Bounds for power injection at each node

# Create a ConcreteModel object using Pyomo and define the sets for the model
model = ConcreteModel('heat network problem')
model.Nodes = Set(initialize=Nodes)  # Set of nodes in the model
model.Pipes = Set(initialize=Pipes)  # Set of pipes in the model
model.TimeSteps = Set(initialize=TimeSteps)  # Set of time steps in the model

# Define the heat cost parameter for each node
heat_cost = {1: 1, 2: 1, 3: -2}  # Heat cost for each node
model.C_H = Param(model.Nodes, initialize=heat_cost)  # Parameter for heat cost in the model

# Define the decision variables for the model
model.m_node = Var(model.Nodes, model.TimeSteps, bounds=lambda model, n, t: m_n_bounds[n])  # Mass flow rates at each node
model.m_pipe = Var(model.Pipes, model.TimeSteps, bounds=lambda model, p, t: m_p_bounds[p])  # Mass flow rates in each pipe
model.Power_injection = Var(model.Nodes, model.TimeSteps, bounds=lambda model, n, t: P_H_bounds[n])  # Power injection at each node

# Mass flow conservation constraint
def mass_flow_conservation(model, n, t):
    return sum(model.m_pipe[p, t] for p in S_n_minus[n]) - sum(model.m_pipe[p, t] for p in S_n_plus[n]) == model.m_node[n, t]

model.mass_flow_conservation = Constraint(Nodes[:-1], model.TimeSteps, rule=mass_flow_conservation)# Constraint for mass flow conservation

cons_expr = model.m_node[3,1] == model.m_pipe['B',1]
model.last_node= Constraint(expr=cons_expr)


# Power injection calculation
def power_injection(model, n, t):
    return c_f * model.m_node[n, t] * (T_Supply - T_Return) == model.Power_injection[n,t]
    
model.power_injection = Constraint(model.Nodes, model.TimeSteps, rule=power_injection) # Calculation of power injection at each node

# # Power balance constraint
# def power_balance_cons(model, t):
#     return sum(power_injection(model, n, t) * model.C_H[n] for n in model.Nodes) == 0

# model.power_balance_cons = Constraint(model.TimeSteps, rule=power_balance_cons)  # Constraint for power balance

# Objective function
def obj_rule(model):
    return sum(model.Power_injection[n, t] * model.C_H[n] for n in model.Nodes for t in model.TimeSteps)

model.obj = Objective(rule=obj_rule, sense=minimize)  # Objective function to minimize the total cost of heat production

model.mass_flow_conservation.pprint()

# Solve the optimization problem
solver = SolverFactory('ipopt')  # Solver for the optimization problem
results = solver.solve(model)  # Solve the model and store the results

# Process and print results
if results.solver.status == SolverStatus.ok and results.solver.termination_condition == TerminationCondition.optimal:
    # Print the constraints and optimal values of the decision variables
    model.mass_flow_conservation.pprint()
    # model.power_balance_cons.pprint()
    model.Power_injection.pprint()

    # Print the optimal values of the decision variables
    print("Optimal mass flow rates at each node and in each pipe:")
    for n in model.Nodes:
        for t in model.TimeSteps:
            print(f"Node {n} at time step {t}: {model.m_node[n, t].value}")
    print("\n")
    for p in model.Pipes:
        for t in model.TimeSteps:
            print(f"Pipe {p} at time step {t}: {model.m_pipe[p, t].value}")

    # Calculate and print power injection at each node
    print("\nOptimal power injection at each node:")
    for n in model.Nodes:
        for t in model.TimeSteps:
            pi = {model.Power_injection[n, t].value}
            print(f"Power injection at node {n} at time step {t}: {pi}")

    # Print the optimal value of the objective function
    print("\nOptimal value of the objective function:", model.obj())

else:
    print("There was an issue with the solver:")
    print(f"Solver status: {results.solver.status}")
    print(f"Termination condition: {results.solver.termination_condition}")
    print(f"Message from solver: {results.solver.message}")

