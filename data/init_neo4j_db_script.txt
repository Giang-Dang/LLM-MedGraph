// ----------------------
// 1.Constraints
// ----------------------
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease)     REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Symptom)     REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Prevention)  REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Treatment)   REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (r:RiskFactor)  REQUIRE r.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (a:AgeGroup)    REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gender)      REQUIRE g.name IS UNIQUE;

// ----------------------
// 2.Create Nodes
// ----------------------
// Diseases
CREATE (:Disease {name:'Influenza'});
CREATE (:Disease {name:'Diabetes'});
CREATE (:Disease {name:'Hypertension'});
CREATE (:Disease {name:'Asthma'});
CREATE (:Disease {name:'Migraine'});

// Symptoms
CREATE (:Symptom {name:'Fever', prevalence:90});
CREATE (:Symptom {name:'Cough', prevalence:80});
CREATE (:Symptom {name:'Fatigue', prevalence:70});
CREATE (:Symptom {name:'Shortness of Breath', prevalence:60});
CREATE (:Symptom {name:'Headache', prevalence:50});
CREATE (:Symptom {name:'Nausea', prevalence:40});
CREATE (:Symptom {name:'Dizziness', prevalence:30});
CREATE (:Symptom {name:'Chest Pain', prevalence:20});
CREATE (:Symptom {name:'Sweating', prevalence:10});
CREATE (:Symptom {name:'Blurred Vision', prevalence:5});

// Preventions
CREATE (:Prevention {name:'Vaccination'});
CREATE (:Prevention {name:'Healthy Diet'});
CREATE (:Prevention {name:'Regular Exercise'});
CREATE (:Prevention {name:'Avoid Allergens'});
CREATE (:Prevention {name:'Stress Management'});

// Treatments
CREATE (:Treatment {name:'Antiviral Medication'});
CREATE (:Treatment {name:'Insulin Therapy'});
CREATE (:Treatment {name:'Antihypertensive Drugs'});
CREATE (:Treatment {name:'Bronchodilators'});
CREATE (:Treatment {name:'Pain Relievers'});

// Risk Factors
CREATE (:RiskFactor {name:'Smoking'});
CREATE (:RiskFactor {name:'Obesity'});
CREATE (:RiskFactor {name:'High Salt Intake'});
CREATE (:RiskFactor {name:'Sedentary Lifestyle'});
CREATE (:RiskFactor {name:'Allergen Exposure'});

// Age Groups
CREATE (:AgeGroup {name:'Children'});
CREATE (:AgeGroup {name:'Adults'});
CREATE (:AgeGroup {name:'Elderly'});

// Genders
CREATE (:Gender {name:'Male'});
CREATE (:Gender {name:'Female'});

// ----------------------
// 3.Disease → Symptom
// ----------------------
MATCH (d:Disease {name:'Influenza'}), (s:Symptom) WHERE s.name IN ['Fever','Cough','Fatigue'] CREATE (d)-[:HAS_SYMPTOM]->(s);
MATCH (d:Disease {name:'Diabetes'}),  (s:Symptom) WHERE s.name IN ['Fatigue','Blurred Vision'] CREATE (d)-[:HAS_SYMPTOM]->(s);
MATCH (d:Disease {name:'Hypertension'}),(s:Symptom) WHERE s.name IN ['Shortness of Breath','Chest Pain'] CREATE (d)-[:HAS_SYMPTOM]->(s);
MATCH (d:Disease {name:'Asthma'}),     (s:Symptom) WHERE s.name IN ['Shortness of Breath','Cough'] CREATE (d)-[:HAS_SYMPTOM]->(s);
MATCH (d:Disease {name:'Migraine'}),   (s:Symptom) WHERE s.name IN ['Headache','Nausea'] CREATE (d)-[:HAS_SYMPTOM]->(s);

// ----------------------
// 4.Disease → Prevention
// ----------------------
MATCH (d:Disease {name:'Influenza'}), (p:Prevention {name:'Vaccination'}) CREATE (d)-[:HAS_PREVENTION]->(p);
MATCH (d:Disease {name:'Diabetes'}),  (p:Prevention {name:'Healthy Diet'}) CREATE (d)-[:HAS_PREVENTION]->(p);
MATCH (d:Disease {name:'Hypertension'}),(p:Prevention {name:'Regular Exercise'}) CREATE (d)-[:HAS_PREVENTION]->(p);
MATCH (d:Disease {name:'Asthma'}),     (p:Prevention {name:'Avoid Allergens'}) CREATE (d)-[:HAS_PREVENTION]->(p);
MATCH (d:Disease {name:'Migraine'}),   (p:Prevention {name:'Stress Management'}) CREATE (d)-[:HAS_PREVENTION]->(p);

// ----------------------
// 5.Disease → Treatment
// ----------------------
MATCH (d:Disease {name:'Influenza'}), (t:Treatment {name:'Antiviral Medication'}) CREATE (d)-[:HAS_TREATMENT]->(t);
MATCH (d:Disease {name:'Diabetes'}),  (t:Treatment {name:'Insulin Therapy'}) CREATE (d)-[:HAS_TREATMENT]->(t);
MATCH (d:Disease {name:'Hypertension'}),(t:Treatment {name:'Antihypertensive Drugs'}) CREATE (d)-[:HAS_TREATMENT]->(t);
MATCH (d:Disease {name:'Asthma'}),     (t:Treatment {name:'Bronchodilators'}) CREATE (d)-[:HAS_TREATMENT]->(t);
MATCH (d:Disease {name:'Migraine'}),   (t:Treatment {name:'Pain Relievers'}) CREATE (d)-[:HAS_TREATMENT]->(t);

// ----------------------
// 6.Disease → RiskFactor
// ----------------------
MATCH (d:Disease {name:'Influenza'}), (r:RiskFactor {name:'Smoking'}) CREATE (d)-[:HAS_RISK_FACTOR]->(r);
MATCH (d:Disease {name:'Diabetes'}),  (r:RiskFactor {name:'Obesity'}) CREATE (d)-[:HAS_RISK_FACTOR]->(r);
MATCH (d:Disease {name:'Hypertension'}),(r:RiskFactor {name:'High Salt Intake'}) CREATE (d)-[:HAS_RISK_FACTOR]->(r);
MATCH (d:Disease {name:'Asthma'}),     (r:RiskFactor {name:'Allergen Exposure'}) CREATE (d)-[:HAS_RISK_FACTOR]->(r);
MATCH (d:Disease {name:'Migraine'}),   (r:RiskFactor {name:'Sedentary Lifestyle'}) CREATE (d)-[:HAS_RISK_FACTOR]->(r);

// ----------------------
// 7.Disease → AgeGroup
// ----------------------
MATCH (d:Disease {name:'Influenza'}), (a:AgeGroup {name:'Children'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Influenza'}), (a:AgeGroup {name:'Adults'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Diabetes'}),  (a:AgeGroup {name:'Adults'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Diabetes'}),  (a:AgeGroup {name:'Elderly'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Hypertension'}),(a:AgeGroup {name:'Elderly'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Asthma'}),     (a:AgeGroup {name:'Children'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Asthma'}),     (a:AgeGroup {name:'Adults'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Migraine'}),   (a:AgeGroup {name:'Adults'}) CREATE (d)-[:AFFECTS]->(a);
MATCH (d:Disease {name:'Migraine'}),   (a:AgeGroup {name:'Elderly'}) CREATE (d)-[:AFFECTS]->(a);

// ----------------------
// 8.Disease → Gender (with prevalence)
// ----------------------
MATCH (d:Disease {name:'Influenza'}), (g:Gender {name:'Male'})   CREATE (d)-[:AFFECTS {prevalence:47}]->(g);
MATCH (d:Disease {name:'Influenza'}), (g:Gender {name:'Female'}) CREATE (d)-[:AFFECTS {prevalence:53}]->(g);

MATCH (d:Disease {name:'Diabetes'}),  (g:Gender {name:'Male'})   CREATE (d)-[:AFFECTS {prevalence:52}]->(g);
MATCH (d:Disease {name:'Diabetes'}),  (g:Gender {name:'Female'}) CREATE (d)-[:AFFECTS {prevalence:48}]->(g);

MATCH (d:Disease {name:'Hypertension'}),(g:Gender {name:'Male'})   CREATE (d)-[:AFFECTS {prevalence:55}]->(g);
MATCH (d:Disease {name:'Hypertension'}),(g:Gender {name:'Female'}) CREATE (d)-[:AFFECTS {prevalence:45}]->(g);

MATCH (d:Disease {name:'Asthma'}),     (g:Gender {name:'Male'})   CREATE (d)-[:AFFECTS {prevalence:40}]->(g);
MATCH (d:Disease {name:'Asthma'}),     (g:Gender {name:'Female'}) CREATE (d)-[:AFFECTS {prevalence:60}]->(g);

MATCH (d:Disease {name:'Migraine'}),   (g:Gender {name:'Male'})   CREATE (d)-[:AFFECTS {prevalence:32}]->(g);
MATCH (d:Disease {name:'Migraine'}),   (g:Gender {name:'Female'}) CREATE (d)-[:AFFECTS {prevalence:68}]->(g);
