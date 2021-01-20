import pandas as pd 
import gurobipy as grb
import sys

class optimizer():

    def __init__(self, path:str=""):
        if == "":
            path="./"
        self.demand = pd.read_csv(path+"Demand.csv", index_col=0)
        self.holding_cost = pd.read_csv(path+"./Holding_Cost.csv", index_col=0)
        self.op_time = pd.read_csv(path+"./Op_Time.csv", index_col=0)
        self.prod_cost = pd.read_csv(path+"./Production_Cost.csv", index_col=0)

        self.d = {(i,j):self.demand.iloc[j,i] for i in range(12) for j in range(3)}
        self.p = {(i,j):self.prod_cost.iloc[j,i] for i in range(12) for j in range(4)}   
        self.c = {(i,j):self.holding_cost.iloc[i,j] for i in range(3) for j in range(2)} 
        self.t = {(i,j):self.op_time.iloc[i,j] for i in range(3) for j in range(4)}      
        self.o1 = [1,2,1]
        self.o2 = [2,3,4] 

        self.model = grb.Model(name="Inventory_Planning")
        self.model.ModelSense = grb.GRB.MINIMIZE

    def add_decision_variables(self, revision:bool=False, cost_reduction:bool=False)->list:

        variables = []

        sc = {(i,j):
        self.model.addVar(vtype=grb.GRB.INTEGER, lb=0, name="Sc_{0}_{1}".format(i,j))
        for i in range(12) for j in range(3)}
        variables.append(sc)
        fc = {(i,j):
        self.model.addVar(vtype=grb.GRB.INTEGER, lb=0, name="Fc_{0}_{1}".format(i,j))
        for i in range(12) for j in range(3)}
        variables.append(fc)
        sw = {(i,j):
        self.model.addVar(vtype=grb.GRB.INTEGER, lb=0, name="Sw_{0}_{1}".format(i,j))
        for i in range(12) for j in range(3)}
        variables.append(sw)
        sp = {(i,j):
        self.model.addVar(vtype=grb.GRB.INTEGER, lb=0, name="Sp_{0}_{1}".format(i,j))
        for i in range(12) for j in range(3)}
        variables.append(sp)
        fp = {(i,j):
        self.model.addVar(vtype=grb.GRB.INTEGER, lb=0, name="Fp_{0}_{1}".format(i,j))
        for i in range(12) for j in range(3)}
        variables.append(fp)
        if revision==True:
            S = {(i,j): self.model.addVar(vtype=grb.GRB.BINARY, name="S_{}_{}".format(i,j))
            for i in range(12) for j in range(4)}
            variables.append(S)
            if cost_reduction == True:
                S2 = {(i,j):self.model.addVar(vtype=grb.GRB.BINARY, name="SS_{}_{}".format(i,j))
                for i in range(12) for j in range(4)}
                variables.append(S2)
        
        return variables

    def add_objective_function(self, decision_variables:list, revision:bool=False, cost_reduction:bool=False)->object:

        if revision == True:
            if cost_reduction == True:
                [sc, fc, sw, sp, fp, S, S2] = decision_variables
            else:
                [sc, fc, sw, sp, fp, S] = decision_variables
        else:
            [sc, fc, sw, sp, fp] = decision_variables

        hc_obj = grb.quicksum((sc[i,j]*self.c[j,0])+(fc[i,j]*self.c[j,1]) for i in range(12) for j in range(3))
        pc_obj = grb.quicksum(((sw[i,j]+fp[i,j])*self.p[i,self.o2[j]-1])+((sp[i,j]+fp[i,j])*self.p[i,self.o1[j]-1]) for i in range(12) for j in range(3))
        obj = pc_obj + hc_obj

        if cost_reduction == True:
            hc_obj = grb.quicksum((sc[i,j]*self.c[j,0])+(fc[i,j]*self.c[j,1]) for i in range(12) for j in range(3))
            pc_obj = grb.quicksum((((sw[i,j]+fp[i,j])*((0.9*self.p[i,self.o2[j]-1])+(0.1*S2[i,self.o2[j]-1]*self.p[i,self.o2[j]-1])))+ ((sp[i,j]+fp[i,j])*((0.9*self.p[i,self.o1[j]-1])+(0.1*S2[i,self.o1[j]-1]*self.p[i,self.o1[j]-1])))) for i in range(12) for j in range(3))
            obj = pc_obj + hc_obj

        return obj

    def add_constraints(self, decision_variables:list, capacity:bool=False, revision:bool=False, cost_reduction:bool=False)->dict:

        if revision == True:
            if cost_reduction == True:
                [sc, fc, sw, sp, fp, S, S2] = decision_variables
            else:
                [sc, fc, sw, sp, fp, S] = decision_variables
        else:
            [sc, fc, sw, sp, fp] = decision_variables

        constraints = {}
        cnt = 0
        for i in range(12):
            for k in range(3):
                constraints[cnt] = self.model.addConstr(lhs=self.d[i,k],
                                                rhs=sw[i,k]+fp[i,k]+fc[i,k],
                                                sense=grb.GRB.LESS_EQUAL,
                                                name="Constraint"+str(cnt))              #Demand constraint
                cnt += 1  
                
        for k in range(3):
            constraints[cnt] = self.model.addConstr(lhs=grb.quicksum(self.d[i,k] for i in range(12)),
                                            rhs=grb.quicksum((sw[i,k]+fp[i,k]) for i in range(12)),
                                            sense=grb.GRB.LESS_EQUAL,
                                            name="Constraint"+str(cnt))                 #Total Demand constraint
            cnt += 1
            

        for k in range(3):
            constraints[cnt] = self.model.addConstr(lhs=fc[0,k]+sc[0,k],
                                                rhs=0,
                                                sense=grb.GRB.EQUAL,
                                                name="Constraint"+str(cnt))                 #First month carry over constraint
            cnt+=1

        for i in range(1,12):
            for k in range(3):
                constraints[cnt] = self.model.addConstr(lhs=fc[i,k],
                                                rhs=fc[i-1,k] + sw[i-1,k] + fp[i-1,k] - self.d[i-1,k],
                                                sense=grb.GRB.EQUAL,
                                                name="Constraint"+str(cnt))                 #Fully finished carry over
                cnt += 1
        for i in range(1,12):
            for k in range(3):
                constraints[cnt] = self.model.addConstr(lhs=sc[i,k],
                                                rhs=sp[i-1,k] + sc[i-1,k] - sw[i-1,k],
                                                sense=grb.GRB.EQUAL,
                                                name="Constraint"+str(cnt))                    #Semi finished carry over
                cnt+= 1
                    
        for k in range(3):
            constraints[cnt] = self.model.addConstr(lhs=sp[11,k]+sc[11,k],
                                            rhs=sw[11,k],
                                            sense=grb.GRB.EQUAL,
                                            name="Constraint"+str(cnt))                        #Last month semi finished products
            cnt+= 1

        if capacity == True:
            for i in range(12):
                constraints[cnt] = self.model.addConstr(lhs=(sp[i,0]+fp[i,0])*self.t[0,0] + (sp[i,2]+fp[i,2])*self.t[2,0],
                                                rhs=550,
                                                sense=grb.GRB.LESS_EQUAL,
                                                name="Constraint"+str(cnt))                         #Capacity1
                cnt+=1      

            for i in range(12):
                constraints[cnt] = self.model.addConstr(lhs=(sw[i,0] + fp[i,0])*self.t[0,1] + (sp[i,1] + fp[i,1])*self.t[1,1],
                                                rhs=750,
                                                sense=grb.GRB.LESS_EQUAL,
                                                name="Constraint"+str(cnt))                       #Capacity2
                cnt+=1   
                
            for i in range(12):
                constraints[cnt] = self.model.addConstr(lhs=(sw[i,1]+fp[i,1])*self.t[1,2],
                                                rhs=450,
                                                sense=grb.GRB.LESS_EQUAL,
                                                name="Constraint"+str(cnt))                     #Capacity3
                cnt+=1 
                    
            for i in range(12):
                constraints[cnt] = self.model.addConstr(lhs=(sw[i,2]+fp[i,2])*self.t[2,3],
                                                rhs=400,
                                                sense=grb.GRB.LESS_EQUAL,
                                                name="Constraint"+str(cnt))                   #Capacity4
                cnt+=1      

        if revision == True:
            for j in range(4):
                constraints[cnt] = self.model.addConstr(lhs=grb.quicksum(S[i,j] for i in range(12)),
                                                rhs=11,
                                                sense=grb.GRB.EQUAL,
                                                name="Constraint"+str(cnt))                 #Revision for one month
                cnt+=1
                
            for i in range(12):
                for k in range(3):
                    constraints[cnt] = self.model.addConstr(lhs=sp[i,k]+fp[i,k],
                                                    rhs=(sp[i,k]+fp[i,k])*S[i,o1[k]-1],
                                                    sense=grb.GRB.EQUAL,
                                                    name="Constraint"+str(cnt))            #Stopping production during revision month
                    cnt+=1
                    
            for i in range(12):
                for k in range(3):
                    constraints[cnt] = self.model.addConstr(lhs=sw[i,k]+fp[i,k],
                                                    rhs=(sw[i,k]+fp[i,k])*S[i,o2[k]-1],
                                                    sense=grb.GRB.EQUAL,
                                                    name="Constraint"+str(cnt))               #Stopping production during revision month
                    cnt+=1

        if cost_reduction == True:
            for j in range(4):
                constraints[cnt] = self.model.addConstr(lhs=S2[1,j],
                                                    rhs=1,
                                                    sense=grb.GRB.EQUAL,
                                                    name="Constraint"+str(cnt))                 #Binary multiplier for first month
                cnt+=1
                
            for i in range(1,12):
                for j in range(4):
                    constraints[cnt] = self.model.addConstr(lhs=S2[i,j],
                                                    rhs=S2[i-1,j]*S[i-1,j],
                                                    sense=grb.GRB.EQUAL,
                                                    name="Constraint"+str(cnt))             #Subsequent months zero

        return constraints
            
    def get_solution(self, decision_variables:list, objectiveFunc: object, case:int) -> None:

        if revision == True:
            if cost_reduction == True:
                [sc, fc, sw, sp, fp, S, S2] = decision_variables
            else:
                [sc, fc, sw, sp, fp, S] = decision_variables
        else:
            [sc, fc, sw, sp, fp] = decision_variables

        self.model.setObective(objectiveFunc)
        self.model.optimize()
        hc=0
        pc=0
        #Printing Production cost and Holding cost
        for i in range(12):
            for j in range(3):
                hc+=(sc[i,j].X*c[j,0])+(fc[i,j].X*c[j,1])
                
                
        for i in range(12):
            for j in range(3):
                pc+=(sw[i,j].X*p[i,o2[j]-1])+(sp[i,j].X*p[i,o1[j]-1])+(fp[i,j].X*(p[i,o1[j]-1]+p[i,o2[j]-1])) 
        
        print("Holding Cost ", hc)
        print("Production Cost ", pc)
        print("Total Cost",(hc+pc),"euros")


        #Printing solution to excel
        solution = []
        for i in range(12):
            for j in range(3):
                if case >=3:
                    solution.append({"Month":demand.columns[i-1],
                                     "Product":j,
                                     "SP":sp[i,j].X,
                                     "SC":sc[i,j].X,
                                     "SW":sw[i,j].X,
                                     "FC":fc[i,j].X,
                                     "FP":fp[i,j].X,
                                     "S1":S[i,0].X,
                                     "S2":S[i,1].X,
                                     "S3":S[i,2].X,
                                     "S4":S[i,3].X})
                else:
                    solution.append({"Month":demand.columns[i],
                                     "Product":j+1,
                                     "SP":sp[i,j].X,
                                     "SC":sc[i,j].X,
                                     "SW":sw[i,j].X,
                                     "FC":fc[i,j].X,
                                     "FP":fp[i,j].X})


        solution = pd.DataFrame(solution)
        solution.to_csv("./Solution_"+int(case)+".csv", index=False)

if __name__ == "__main__":

    planner = optimize()
    case = sys.argv[0]

    if case == 1:
        decision_variables = planner.add_decision_variables()
        obj_func = planner.add_objective_function(decision_variables)
        constraints = planner.add_constraints(decision_variables)

    if case == 2:
        decision_variables = planner.add_decision_variables()
        obj_func = planner.add_objective_function(decision_variables)
        constraints = planner.add_constraints(decision_variables,True)  

    if case == 3:
        decision_variables = planner.add_decision_variables(True)
        obj_func = planner.add_objective_function(decision_variables, True)
        constraints = planner.add_constraints(decision_variables,True, True)

    if case == 4:
        decision_variables = planner.add_decision_variables(True, True)
        obj_func = planner.add_objective_function(decision_variables, True, True)
        constraints = planner.add_constraints(decision_variables,True, True, True)

    planner.get_solution(decision_variables, objectiveFunc, case)
    