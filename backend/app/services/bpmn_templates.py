"""Built-in BPMN templates (Python-expression conditions, verified against SpiffWorkflow 3.2).

Generic approval process:
  start -> L1 approval -> (rejected? -> rejected end)
        -> amount > 1000 -> countersign (multi-instance, or-sign) -> end approved
        -> else -> L2 approval -> end approved

Node -> assignee variable conventions (resolved by approval_service):
  ut_l1   <- variables["approver_l1"]  (user id)
  ut_l2   <- variables["approver_l2"]  (user id)
  ut_cs   <- variables["countersigners"] (list of user ids, parallel instances)
"""

GENERIC_APPROVAL_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  id="Defs_GenericApproval" targetNamespace="http://prjhub.local/bpmn">
  <bpmn:process id="Generic_Approval" isExecutable="true">
    <bpmn:startEvent id="start"><bpmn:outgoing>f1</bpmn:outgoing></bpmn:startEvent>

    <bpmn:userTask id="ut_l1" name="一级审批">
      <bpmn:incoming>f1</bpmn:incoming><bpmn:outgoing>g1</bpmn:outgoing>
    </bpmn:userTask>

    <bpmn:exclusiveGateway id="gw_rej1" gatewayDirection="Diverging" default="g1_ok">
      <bpmn:incoming>g1</bpmn:incoming>
      <bpmn:outgoing>g1_no</bpmn:outgoing><bpmn:outgoing>g1_ok</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <bpmn:exclusiveGateway id="gw_amount" gatewayDirection="Diverging" default="f_small">
      <bpmn:incoming>g1_ok</bpmn:incoming>
      <bpmn:outgoing>f_big</bpmn:outgoing><bpmn:outgoing>f_small</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <bpmn:userTask id="ut_cs" name="会签审批">
      <bpmn:multiInstanceLoopCharacteristics isSequential="false">
        <bpmn:loopCardinality>cs_total</bpmn:loopCardinality>
        <bpmn:completionCondition>completed_count &gt;= cs_pass</bpmn:completionCondition>
      </bpmn:multiInstanceLoopCharacteristics>
      <bpmn:incoming>f_big</bpmn:incoming><bpmn:outgoing>g2</bpmn:outgoing>
    </bpmn:userTask>

    <bpmn:exclusiveGateway id="gw_rej2" gatewayDirection="Diverging" default="g2_ok">
      <bpmn:incoming>g2</bpmn:incoming>
      <bpmn:outgoing>g2_no</bpmn:outgoing><bpmn:outgoing>g2_ok</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <bpmn:userTask id="ut_l2" name="二级审批">
      <bpmn:incoming>f_small</bpmn:incoming><bpmn:outgoing>g3</bpmn:outgoing>
    </bpmn:userTask>

    <bpmn:exclusiveGateway id="gw_rej3" gatewayDirection="Diverging" default="g3_ok">
      <bpmn:incoming>g3</bpmn:incoming>
      <bpmn:outgoing>g3_no</bpmn:outgoing><bpmn:outgoing>g3_ok</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <bpmn:endEvent id="end_approved" name="审批通过"><bpmn:incoming>g2_ok</bpmn:incoming><bpmn:incoming>g3_ok</bpmn:incoming></bpmn:endEvent>
    <bpmn:endEvent id="end_rejected" name="审批驳回"><bpmn:incoming>g1_no</bpmn:incoming><bpmn:incoming>g2_no</bpmn:incoming><bpmn:incoming>g3_no</bpmn:incoming></bpmn:endEvent>

    <bpmn:sequenceFlow id="f1" sourceRef="start" targetRef="ut_l1"/>
    <bpmn:sequenceFlow id="g1" sourceRef="ut_l1" targetRef="gw_rej1"/>
    <bpmn:sequenceFlow id="g1_no" name="驳回" sourceRef="gw_rej1" targetRef="end_rejected">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">rejected</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="g1_ok" sourceRef="gw_rej1" targetRef="gw_amount"/>
    <bpmn:sequenceFlow id="f_big" name="大额" sourceRef="gw_amount" targetRef="ut_cs">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">amount &gt; 1000</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="f_small" name="小额" sourceRef="gw_amount" targetRef="ut_l2"/>
    <bpmn:sequenceFlow id="g2" sourceRef="ut_cs" targetRef="gw_rej2"/>
    <bpmn:sequenceFlow id="g2_no" name="驳回" sourceRef="gw_rej2" targetRef="end_rejected">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">rejected</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="g2_ok" sourceRef="gw_rej2" targetRef="end_approved"/>
    <bpmn:sequenceFlow id="g3" sourceRef="ut_l2" targetRef="gw_rej3"/>
    <bpmn:sequenceFlow id="g3_no" name="驳回" sourceRef="gw_rej3" targetRef="end_rejected">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">rejected</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="g3_ok" sourceRef="gw_rej3" targetRef="end_approved"/>
  </bpmn:process>
</bpmn:definitions>
"""


PARALLEL_APPROVAL_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  id="Defs_ParallelApproval" targetNamespace="http://prjhub.local/bpmn">
  <bpmn:process id="Parallel_Approval" isExecutable="true">
    <bpmn:startEvent id="start"><bpmn:outgoing>p0</bpmn:outgoing></bpmn:startEvent>

    <bpmn:userTask id="ut_l1" name="一级审批">
      <bpmn:incoming>p0</bpmn:incoming><bpmn:outgoing>pg1</bpmn:outgoing>
    </bpmn:userTask>

    <bpmn:exclusiveGateway id="gw_rej1" gatewayDirection="Diverging" default="pg_ok">
      <bpmn:incoming>pg1</bpmn:incoming>
      <bpmn:outgoing>pg_no</bpmn:outgoing><bpmn:outgoing>pg_ok</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <bpmn:parallelGateway id="fork" gatewayDirection="Diverging">
      <bpmn:incoming>pg_ok</bpmn:incoming>
      <bpmn:outgoing>pfa</bpmn:outgoing><bpmn:outgoing>pfb</bpmn:outgoing>
    </bpmn:parallelGateway>

    <bpmn:userTask id="ut_fin" name="财务审批">
      <bpmn:incoming>pfa</bpmn:incoming><bpmn:outgoing>pgf</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:exclusiveGateway id="gw_rf" gatewayDirection="Diverging" default="pf_join">
      <bpmn:incoming>pgf</bpmn:incoming>
      <bpmn:outgoing>pf_no</bpmn:outgoing><bpmn:outgoing>pf_join</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <bpmn:userTask id="ut_tech" name="技术评审">
      <bpmn:incoming>pfb</bpmn:incoming><bpmn:outgoing>pgt</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:exclusiveGateway id="gw_rt" gatewayDirection="Diverging" default="pt_join">
      <bpmn:incoming>pgt</bpmn:incoming>
      <bpmn:outgoing>pt_no</bpmn:outgoing><bpmn:outgoing>pt_join</bpmn:outgoing>
    </bpmn:exclusiveGateway>

    <bpmn:parallelGateway id="join" gatewayDirection="Converging">
      <bpmn:incoming>pf_join</bpmn:incoming><bpmn:incoming>pt_join</bpmn:incoming>
      <bpmn:outgoing>pf_end</bpmn:outgoing>
    </bpmn:parallelGateway>

    <bpmn:endEvent id="end_approved" name="审批通过"><bpmn:incoming>pf_end</bpmn:incoming></bpmn:endEvent>
    <bpmn:endEvent id="end_rejected" name="审批驳回">
      <bpmn:incoming>pg_no</bpmn:incoming><bpmn:incoming>pf_no</bpmn:incoming><bpmn:incoming>pt_no</bpmn:incoming>
      <bpmn:terminateEventDefinition/>
    </bpmn:endEvent>

    <bpmn:sequenceFlow id="p0" sourceRef="start" targetRef="ut_l1"/>
    <bpmn:sequenceFlow id="pg1" sourceRef="ut_l1" targetRef="gw_rej1"/>
    <bpmn:sequenceFlow id="pg_no" name="驳回" sourceRef="gw_rej1" targetRef="end_rejected">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">rejected</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="pg_ok" sourceRef="gw_rej1" targetRef="fork"/>
    <bpmn:sequenceFlow id="pfa" sourceRef="fork" targetRef="ut_fin"/>
    <bpmn:sequenceFlow id="pfb" sourceRef="fork" targetRef="ut_tech"/>
    <bpmn:sequenceFlow id="pgf" sourceRef="ut_fin" targetRef="gw_rf"/>
    <bpmn:sequenceFlow id="pf_no" name="驳回" sourceRef="gw_rf" targetRef="end_rejected">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">rejected</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="pf_join" sourceRef="gw_rf" targetRef="join"/>
    <bpmn:sequenceFlow id="pgt" sourceRef="ut_tech" targetRef="gw_rt"/>
    <bpmn:sequenceFlow id="pt_no" name="驳回" sourceRef="gw_rt" targetRef="end_rejected">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">rejected</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="pt_join" sourceRef="gw_rt" targetRef="join"/>
    <bpmn:sequenceFlow id="pf_end" sourceRef="join" targetRef="end_approved"/>
  </bpmn:process>
</bpmn:definitions>
"""
