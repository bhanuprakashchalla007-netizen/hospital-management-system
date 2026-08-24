/*
 ============================================================
  Hospital Management System — C++ with JSON File Persistence
  LLT-1: Application Development Using Design Concepts
 ============================================================
  Data is saved to: data/hospital_data.json
  Flask dashboard reads the SAME file to show reports.
 ============================================================
*/

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <iomanip>
#include <sstream>
#include <ctime>
using namespace std;

// ─────────────────────────────────────────
//  UTILITY: Simple JSON helpers
// ─────────────────────────────────────────
string jsonStr(const string& key, const string& val, bool last = false) {
    return "\"" + key + "\": \"" + val + "\"" + (last ? "" : ",");
}
string jsonNum(const string& key, double val, bool last = false) {
    ostringstream oss;
    oss << fixed << setprecision(2) << val;
    return "\"" + key + "\": " + oss.str() + (last ? "" : ",");
}
string jsonInt(const string& key, int val, bool last = false) {
    return "\"" + key + "\": " + to_string(val) + (last ? "" : ",");
}
string jsonBool(const string& key, bool val, bool last = false) {
    return "\"" + key + "\": " + (val ? "true" : "false") + (last ? "" : ",");
}
string today() {
    time_t t = time(nullptr);
    tm* now = localtime(&t);
    char buf[12];
    strftime(buf, sizeof(buf), "%Y-%m-%d", now);
    return string(buf);
}

// ─────────────────────────────────────────
//  BASE CLASS: Person
// ─────────────────────────────────────────
class Person {
protected:
    int    id;
    string name;
    int    age;
    string phone;
public:
    Person(int id, string name, int age, string phone)
        : id(id), name(name), age(age), phone(phone) {}

    virtual void displayInfo() const {
        cout << "  ID    : " << id    << "\n"
             << "  Name  : " << name  << "\n"
             << "  Age   : " << age   << "\n"
             << "  Phone : " << phone << "\n";
    }
    virtual string toJSON() const = 0;

    int    getId()   const { return id; }
    string getName() const { return name; }
    virtual ~Person() {}
};

// ─────────────────────────────────────────
//  DERIVED CLASS: Patient
// ─────────────────────────────────────────
class Patient : public Person {
private:
    string disease;
    string bloodGroup;
    string admissionDate;
public:
    Patient(int id, string name, int age, string phone,
            string disease, string bloodGroup, string admissionDate)
        : Person(id, name, age, phone),
          disease(disease), bloodGroup(bloodGroup), admissionDate(admissionDate) {}

    void displayInfo() const override {
        cout << "\n  ── Patient ──────────────────────────\n";
        Person::displayInfo();
        cout << "  Disease    : " << disease       << "\n"
             << "  Blood      : " << bloodGroup    << "\n"
             << "  Admitted   : " << admissionDate << "\n";
    }

    string toJSON() const override {
        return "    {\n"
               "      " + jsonInt("id", id)                   + "\n"
               "      " + jsonStr("name", name)               + "\n"
               "      " + jsonInt("age", age)                 + "\n"
               "      " + jsonStr("phone", phone)             + "\n"
               "      " + jsonStr("disease", disease)         + "\n"
               "      " + jsonStr("blood_group", bloodGroup)  + "\n"
               "      " + jsonStr("admission_date", admissionDate, true) + "\n"
               "    }";
    }

    string getDisease()    const { return disease; }
    string getBloodGroup() const { return bloodGroup; }
};

// ─────────────────────────────────────────
//  DERIVED CLASS: Doctor
// ─────────────────────────────────────────
class Doctor : public Person {
private:
    string specialization;
    string department;
    double consultationFee;
public:
    Doctor(int id, string name, int age, string phone,
           string specialization, string department, double fee)
        : Person(id, name, age, phone),
          specialization(specialization), department(department), consultationFee(fee) {}

    void displayInfo() const override {
        cout << "\n  ── Doctor ───────────────────────────\n";
        Person::displayInfo();
        cout << "  Specialization : " << specialization  << "\n"
             << "  Department     : " << department      << "\n"
             << "  Fee            : Rs." << fixed << setprecision(2) << consultationFee << "\n";
    }

    string toJSON() const override {
        return "    {\n"
               "      " + jsonInt("id", id)                          + "\n"
               "      " + jsonStr("name", name)                      + "\n"
               "      " + jsonInt("age", age)                        + "\n"
               "      " + jsonStr("phone", phone)                    + "\n"
               "      " + jsonStr("specialization", specialization)  + "\n"
               "      " + jsonStr("department", department)          + "\n"
               "      " + jsonNum("consultation_fee", consultationFee, true) + "\n"
               "    }";
    }

    string getSpecialization() const { return specialization; }
    double getFee()            const { return consultationFee; }
};

// ─────────────────────────────────────────
//  CLASS: Appointment
// ─────────────────────────────────────────
class Appointment {
private:
    int    appointmentId;
    int    patientId;
    int    doctorId;
    string patientName;
    string doctorName;
    string date;
    string timeSlot;
    string status;
public:
    Appointment(int aId, int pId, int dId,
                string pName, string dName,
                string date, string time)
        : appointmentId(aId), patientId(pId), doctorId(dId),
          patientName(pName), doctorName(dName),
          date(date), timeSlot(time), status("Scheduled") {}

    void display() const {
        cout << "\n  ── Appointment ──────────────────────\n"
             << "  Appt ID  : " << appointmentId << "\n"
             << "  Patient  : " << patientName   << " (ID:" << patientId << ")\n"
             << "  Doctor   : " << doctorName    << " (ID:" << doctorId  << ")\n"
             << "  Date     : " << date          << "\n"
             << "  Time     : " << timeSlot      << "\n"
             << "  Status   : " << status        << "\n";
    }

    string toJSON() const {
        return "    {\n"
               "      " + jsonInt("id", appointmentId)          + "\n"
               "      " + jsonInt("patient_id", patientId)      + "\n"
               "      " + jsonInt("doctor_id", doctorId)        + "\n"
               "      " + jsonStr("patient_name", patientName)  + "\n"
               "      " + jsonStr("doctor_name", doctorName)    + "\n"
               "      " + jsonStr("date", date)                 + "\n"
               "      " + jsonStr("time_slot", timeSlot)        + "\n"
               "      " + jsonStr("status", status, true)       + "\n"
               "    }";
    }

    void complete() { status = "Completed"; }
    void cancel()   { status = "Cancelled"; }

    int    getId()     const { return appointmentId; }
    string getStatus() const { return status; }
};

// ─────────────────────────────────────────
//  CLASS: Bill
// ─────────────────────────────────────────
class Bill {
private:
    int    billId;
    int    patientId;
    string patientName;
    string doctorName;
    double consultationFee;
    double medicineCost;
    double roomCharge;
    double totalAmount;
    bool   isPaid;
    string billDate;
public:
    Bill(int bId, int pId, string pName, string dName,
         double consFee, double medCost, double roomCharge)
        : billId(bId), patientId(pId), patientName(pName), doctorName(dName),
          consultationFee(consFee), medicineCost(medCost), roomCharge(roomCharge),
          totalAmount(consFee + medCost + roomCharge), isPaid(false), billDate(today()) {}

    void display() const {
        cout << "\n  ══════════════════════════════════\n"
             << "           HOSPITAL BILL\n"
             << "  ══════════════════════════════════\n"
             << "  Bill ID     : " << billId      << "\n"
             << "  Patient     : " << patientName << "\n"
             << "  Doctor      : " << doctorName  << "\n"
             << "  Date        : " << billDate    << "\n"
             << "  ──────────────────────────────────\n"
             << "  Consultation: Rs." << fixed << setprecision(2) << consultationFee << "\n"
             << "  Medicine    : Rs." << medicineCost << "\n"
             << "  Room        : Rs." << roomCharge   << "\n"
             << "  ──────────────────────────────────\n"
             << "  TOTAL       : Rs." << totalAmount  << "\n"
             << "  Status      : " << (isPaid ? "PAID" : "PENDING") << "\n"
             << "  ══════════════════════════════════\n";
    }

    string toJSON() const {
        return "    {\n"
               "      " + jsonInt("id", billId)                          + "\n"
               "      " + jsonInt("patient_id", patientId)               + "\n"
               "      " + jsonStr("patient_name", patientName)           + "\n"
               "      " + jsonStr("doctor_name", doctorName)             + "\n"
               "      " + jsonNum("consultation_fee", consultationFee)   + "\n"
               "      " + jsonNum("medicine_cost", medicineCost)         + "\n"
               "      " + jsonNum("room_charge", roomCharge)             + "\n"
               "      " + jsonNum("total_amount", totalAmount)           + "\n"
               "      " + jsonBool("is_paid", isPaid)                    + "\n"
               "      " + jsonStr("bill_date", billDate, true)           + "\n"
               "    }";
    }

    void pay() { isPaid = true; }
    int    getId()     const { return billId; }
    double getTotal()  const { return totalAmount; }
    bool   getPaid()   const { return isPaid; }
};

// ─────────────────────────────────────────
//  CLASS: Hospital
// ─────────────────────────────────────────
class Hospital {
private:
    string              hospitalName;
    vector<Patient>     patients;
    vector<Doctor>      doctors;
    vector<Appointment> appointments;
    vector<Bill>        bills;

    int nextPatientId     = 1001;
    int nextDoctorId      = 2001;
    int nextAppointmentId = 3001;
    int nextBillId        = 4001;

    const string DATA_FILE = "data/hospital_data.json";

    // ── JSON save ─────────────────────────
    void saveToFile() {
        ofstream f(DATA_FILE);
        if (!f.is_open()) {
            cout << "  [WARNING] Could not save to file.\n";
            return;
        }

        f << "{\n";
        f << "  \"hospital\": \"" << hospitalName << "\",\n";

        // Patients
        f << "  \"patients\": [\n";
        for (size_t i = 0; i < patients.size(); ++i)
            f << patients[i].toJSON() << (i+1 < patients.size() ? "," : "") << "\n";
        f << "  ],\n";

        // Doctors
        f << "  \"doctors\": [\n";
        for (size_t i = 0; i < doctors.size(); ++i)
            f << doctors[i].toJSON() << (i+1 < doctors.size() ? "," : "") << "\n";
        f << "  ],\n";

        // Appointments
        f << "  \"appointments\": [\n";
        for (size_t i = 0; i < appointments.size(); ++i)
            f << appointments[i].toJSON() << (i+1 < appointments.size() ? "," : "") << "\n";
        f << "  ],\n";

        // Bills
        f << "  \"bills\": [\n";
        for (size_t i = 0; i < bills.size(); ++i)
            f << bills[i].toJSON() << (i+1 < bills.size() ? "," : "") << "\n";
        f << "  ],\n";

        // ID counters
        f << "  \"id_counters\": {\n";
        f << "    \"next_patient_id\": "     << nextPatientId     << ",\n";
        f << "    \"next_doctor_id\": "      << nextDoctorId      << ",\n";
        f << "    \"next_appointment_id\": " << nextAppointmentId << ",\n";
        f << "    \"next_bill_id\": "        << nextBillId        << "\n";
        f << "  }\n";
        f << "}\n";

        f.close();
        cout << "  [Saved] Data written to " << DATA_FILE << "\n";
    }

    // ── Simple JSON field extractor ────────
    string extractField(const string& json, const string& key) {
        string search = "\"" + key + "\": \"";
        size_t pos = json.find(search);
        if (pos == string::npos) {
            // Try numeric
            search = "\"" + key + "\": ";
            pos = json.find(search);
            if (pos == string::npos) return "";
            pos += search.size();
            size_t end = json.find_first_of(",\n}", pos);
            return json.substr(pos, end - pos);
        }
        pos += search.size();
        size_t end = json.find("\"", pos);
        return json.substr(pos, end - pos);
    }

    // ── JSON load ─────────────────────────
    void loadFromFile() {
        ifstream f(DATA_FILE);
        if (!f.is_open()) {
            cout << "  [Info] No saved data found. Starting fresh.\n";
            return;
        }

        string content((istreambuf_iterator<char>(f)), istreambuf_iterator<char>());
        f.close();

        // Load ID counters
        size_t counterPos = content.find("\"id_counters\"");
        if (counterPos != string::npos) {
            string sub = content.substr(counterPos);
            string np = extractField(sub, "next_patient_id");
            string nd = extractField(sub, "next_doctor_id");
            string na = extractField(sub, "next_appointment_id");
            string nb = extractField(sub, "next_bill_id");
            if (!np.empty()) nextPatientId     = stoi(np);
            if (!nd.empty()) nextDoctorId      = stoi(nd);
            if (!na.empty()) nextAppointmentId = stoi(na);
            if (!nb.empty()) nextBillId        = stoi(nb);
        }

        // Load patients
        size_t pStart = content.find("\"patients\"");
        size_t pEnd   = content.find("\"doctors\"");
        if (pStart != string::npos && pEnd != string::npos) {
            string pSection = content.substr(pStart, pEnd - pStart);
            size_t obj = 0;
            while ((obj = pSection.find("{", obj)) != string::npos) {
                size_t objEnd = pSection.find("}", obj);
                if (objEnd == string::npos) break;
                string rec = pSection.substr(obj, objEnd - obj + 1);
                string sid  = extractField(rec, "id");
                string nm   = extractField(rec, "name");
                string sage = extractField(rec, "age");
                string ph   = extractField(rec, "phone");
                string dis  = extractField(rec, "disease");
                string bl   = extractField(rec, "blood_group");
                string dt   = extractField(rec, "admission_date");
                if (!sid.empty() && !nm.empty())
                    patients.emplace_back(stoi(sid), nm, stoi(sage), ph, dis, bl, dt);
                obj = objEnd + 1;
            }
        }

        // Load doctors
        size_t dStart = content.find("\"doctors\"");
        size_t dEnd   = content.find("\"appointments\"");
        if (dStart != string::npos && dEnd != string::npos) {
            string dSection = content.substr(dStart, dEnd - dStart);
            size_t obj = 0;
            while ((obj = dSection.find("{", obj)) != string::npos) {
                size_t objEnd = dSection.find("}", obj);
                if (objEnd == string::npos) break;
                string rec  = dSection.substr(obj, objEnd - obj + 1);
                string sid  = extractField(rec, "id");
                string nm   = extractField(rec, "name");
                string sage = extractField(rec, "age");
                string ph   = extractField(rec, "phone");
                string sp   = extractField(rec, "specialization");
                string dep  = extractField(rec, "department");
                string fee  = extractField(rec, "consultation_fee");
                if (!sid.empty() && !nm.empty())
                    doctors.emplace_back(stoi(sid), nm, stoi(sage), ph, sp, dep, stod(fee));
                obj = objEnd + 1;
            }
        }

        // Load appointments
        size_t aStart = content.find("\"appointments\"");
        size_t aEnd   = content.find("\"bills\"");
        if (aStart != string::npos && aEnd != string::npos) {
            string aSection = content.substr(aStart, aEnd - aStart);
            size_t obj = 0;
            while ((obj = aSection.find("{", obj)) != string::npos) {
                size_t objEnd = aSection.find("}", obj);
                if (objEnd == string::npos) break;
                string rec  = aSection.substr(obj, objEnd - obj + 1);
                string sid  = extractField(rec, "id");
                string pid  = extractField(rec, "patient_id");
                string did  = extractField(rec, "doctor_id");
                string pnm  = extractField(rec, "patient_name");
                string dnm  = extractField(rec, "doctor_name");
                string dt   = extractField(rec, "date");
                string tm   = extractField(rec, "time_slot");
                string st   = extractField(rec, "status");
                if (!sid.empty()) {
                    Appointment a(stoi(sid), stoi(pid), stoi(did), pnm, dnm, dt, tm);
                    if (st == "Completed") a.complete();
                    if (st == "Cancelled") a.cancel();
                    appointments.push_back(a);
                }
                obj = objEnd + 1;
            }
        }

        // Load bills
        size_t bStart = content.find("\"bills\"");
        size_t bEnd   = content.find("\"id_counters\"");
        if (bStart != string::npos && bEnd != string::npos) {
            string bSection = content.substr(bStart, bEnd - bStart);
            size_t obj = 0;
            while ((obj = bSection.find("{", obj)) != string::npos) {
                size_t objEnd = bSection.find("}", obj);
                if (objEnd == string::npos) break;
                string rec  = bSection.substr(obj, objEnd - obj + 1);
                string sid  = extractField(rec, "id");
                string pid  = extractField(rec, "patient_id");
                string pnm  = extractField(rec, "patient_name");
                string dnm  = extractField(rec, "doctor_name");
                string cf   = extractField(rec, "consultation_fee");
                string mc   = extractField(rec, "medicine_cost");
                string rc   = extractField(rec, "room_charge");
                string paid = extractField(rec, "is_paid");
                if (!sid.empty()) {
                    Bill b(stoi(sid), stoi(pid), pnm, dnm, stod(cf), stod(mc), stod(rc));
                    if (paid == "true") b.pay();
                    bills.push_back(b);
                }
                obj = objEnd + 1;
            }
        }

        cout << "  [Loaded] " << patients.size() << " patients, "
             << doctors.size()      << " doctors, "
             << appointments.size() << " appointments, "
             << bills.size()        << " bills from " << DATA_FILE << "\n";
    }

    // ── Helpers ───────────────────────────
    Patient* findPatient(int id) {
        for (auto& p : patients) if (p.getId() == id) return &p;
        return nullptr;
    }
    Doctor* findDoctor(int id) {
        for (auto& d : doctors) if (d.getId() == id) return &d;
        return nullptr;
    }

public:
    Hospital(string name) : hospitalName(name) { loadFromFile(); }

    // ── Register Patient ──────────────────
    void registerPatient() {
        string name, phone, disease, blood, date;
        int age;
        cout << "\n  ── Register Patient ────────────────\n";
        cout << "  Name         : "; cin.ignore(); getline(cin, name);
        cout << "  Age          : "; cin >> age;
        cout << "  Phone        : "; cin >> phone;
        cout << "  Disease      : "; cin.ignore(); getline(cin, disease);
        cout << "  Blood Group  : "; cin >> blood;
        cout << "  Admission Date (YYYY-MM-DD): "; cin >> date;
        patients.emplace_back(nextPatientId, name, age, phone, disease, blood, date);
        cout << "\n  Patient registered. ID: " << nextPatientId++ << "\n";
        saveToFile();
    }

    // ── Add Doctor ────────────────────────
    void addDoctor() {
        string name, phone, spec, dept;
        int age; double fee;
        cout << "\n  ── Add Doctor ──────────────────────\n";
        cout << "  Name           : "; cin.ignore(); getline(cin, name);
        cout << "  Age            : "; cin >> age;
        cout << "  Phone          : "; cin >> phone;
        cout << "  Specialization : "; cin.ignore(); getline(cin, spec);
        cout << "  Department     : "; getline(cin, dept);
        cout << "  Consultation Fee (Rs.): "; cin >> fee;
        doctors.emplace_back(nextDoctorId, name, age, phone, spec, dept, fee);
        cout << "\n  Doctor added. ID: " << nextDoctorId++ << "\n";
        saveToFile();
    }

    // ── Book Appointment ──────────────────
    void bookAppointment() {
        int pId, dId;
        string date, time;
        cout << "\n  ── Book Appointment ────────────────\n";
        displayAllPatients();
        cout << "  Patient ID : "; cin >> pId;
        displayAllDoctors();
        cout << "  Doctor  ID : "; cin >> dId;
        Patient* p = findPatient(pId);
        Doctor*  d = findDoctor(dId);
        if (!p) { cout << "  Patient not found.\n"; return; }
        if (!d) { cout << "  Doctor not found.\n";  return; }
        cout << "  Date (YYYY-MM-DD): "; cin >> date;
        cout << "  Time Slot        : "; cin >> time;
        appointments.emplace_back(nextAppointmentId, pId, dId, p->getName(), d->getName(), date, time);
        cout << "\n  Appointment booked. ID: " << nextAppointmentId++ << "\n";
        saveToFile();
    }

    // ── Generate Bill ─────────────────────
    void generateBill() {
        int pId, dId; double medCost, roomCharge;
        cout << "\n  ── Generate Bill ───────────────────\n";
        cout << "  Patient ID    : "; cin >> pId;
        cout << "  Doctor  ID    : "; cin >> dId;
        Patient* p = findPatient(pId);
        Doctor*  d = findDoctor(dId);
        if (!p) { cout << "  Patient not found.\n"; return; }
        if (!d) { cout << "  Doctor not found.\n";  return; }
        cout << "  Medicine Cost : Rs."; cin >> medCost;
        cout << "  Room Charge   : Rs."; cin >> roomCharge;
        bills.emplace_back(nextBillId, pId, p->getName(), d->getName(), d->getFee(), medCost, roomCharge);
        bills.back().display();
        nextBillId++;
        saveToFile();
    }

    // ── Display All ───────────────────────
    void displayAllPatients() const {
        if (patients.empty()) { cout << "\n  No patients.\n"; return; }
        cout << "\n  ── Patients ────────────────────────\n";
        for (const auto& p : patients) p.displayInfo();
    }
    void displayAllDoctors() const {
        if (doctors.empty()) { cout << "\n  No doctors.\n"; return; }
        cout << "\n  ── Doctors ─────────────────────────\n";
        for (const auto& d : doctors) d.displayInfo();
    }
    void displayAllAppointments() const {
        if (appointments.empty()) { cout << "\n  No appointments.\n"; return; }
        cout << "\n  ── Appointments ────────────────────\n";
        for (const auto& a : appointments) a.display();
    }
    void displayAllBills() const {
        if (bills.empty()) { cout << "\n  No bills.\n"; return; }
        cout << "\n  ── Bills ───────────────────────────\n";
        for (const auto& b : bills) b.display();
    }

    // ── Main Menu ─────────────────────────
    void run() {
        int choice;
        cout << "\n  ╔══════════════════════════════════╗\n"
             << "  ║   " << hospitalName << "     ║\n"
             << "  ╚══════════════════════════════════╝\n";
        do {
            cout << "\n  ── MENU ────────────────────────────\n"
                 << "  1. Register Patient\n"
                 << "  2. Add Doctor\n"
                 << "  3. Book Appointment\n"
                 << "  4. Generate Bill\n"
                 << "  5. View All Patients\n"
                 << "  6. View All Doctors\n"
                 << "  7. View All Appointments\n"
                 << "  8. View All Bills\n"
                 << "  0. Exit\n"
                 << "  ────────────────────────────────────\n"
                 << "  Choice: ";
            cin >> choice;
            switch (choice) {
                case 1: registerPatient();       break;
                case 2: addDoctor();             break;
                case 3: bookAppointment();       break;
                case 4: generateBill();          break;
                case 5: displayAllPatients();    break;
                case 6: displayAllDoctors();     break;
                case 7: displayAllAppointments(); break;
                case 8: displayAllBills();       break;
                case 0: cout << "\n  Data saved. Goodbye!\n"; break;
                default: cout << "  Invalid choice.\n";
            }
        } while (choice != 0);
    }
};

// ─────────────────────────────────────────
//  MAIN
// ─────────────────────────────────────────
int main() {
    Hospital h("City General Hospital");
    h.run();
    return 0;
}
