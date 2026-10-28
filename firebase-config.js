/**
 * SIH26190 Legal Document Management System
 * Firebase Integration & Configuration Module
 * 
 * To connect your own live Firebase project:
 * 1. Go to https://console.firebase.google.com/
 * 2. Create a project and register a Web App.
 * 3. Copy your project credentials and paste them below into `FIREBASE_CONFIG`.
 * 4. Enable "Cloud Firestore" and "Firebase Storage".
 */

const FIREBASE_CONFIG = {
  apiKey: "AIzaSyDEMO-KEY-REPLACE-WITH-YOUR-KEY",
  authDomain: "mha-legal-dms.firebaseapp.com",
  projectId: "mha-legal-dms",
  storageBucket: "mha-legal-dms.appspot.com",
  messagingSenderId: "109823901234",
  appId: "1:109823901234:web:ab98ef76cd54"
};

let firebaseApp = null;
let firestoreDb = null;
let firebaseStorage = null;
let isFirebaseActive = false;

function initFirebase() {
  if (typeof firebase === "undefined") {
    console.log("[Firebase] SDK script not loaded yet.");
    return false;
  }

  // Detect if user has provided real credentials or still using demo placeholder
  const isPlaceholder = FIREBASE_CONFIG.apiKey.includes("DEMO-KEY");

  try {
    if (!firebase.apps.length) {
      firebaseApp = firebase.initializeApp(FIREBASE_CONFIG);
    } else {
      firebaseApp = firebase.app();
    }
    firestoreDb = firebase.firestore();
    firebaseStorage = firebase.storage();
    
    // Only set active if real credentials provided and initialized
    if (!isPlaceholder) {
      isFirebaseActive = true;
      console.log("[Firebase] Connected to live Cloud Firestore:", FIREBASE_CONFIG.projectId);
    } else {
      console.log("[Firebase] Initialized with demo configuration. Ready for real keys.");
    }
    return true;
  } catch (err) {
    console.warn("[Firebase] Initialization notice:", err.message);
    isFirebaseActive = false;
    return false;
  }
}

/**
 * Save document metadata and classification to Firestore
 */
async function saveDocumentToFirestore(caseId, docData) {
  if (!isFirebaseActive || !firestoreDb) return null;
  try {
    const docRef = await firestoreDb.collection("cases").doc(caseId)
      .collection("documents").add({
        filename: docData.filename,
        file_size: docData.size,
        doc_type: docData.doc_type,
        is_evidence: docData.is_evidence,
        sha256_hash: docData.sha256,
        classification: docData.classification,
        class_confidence: docData.confidence,
        class_status: "auto",
        uploader_id: docData.uploader_id,
        created_at: firebase.firestore.FieldValue.serverTimestamp()
      });
    return docRef.id;
  } catch (err) {
    console.error("[Firebase] Error saving to Firestore:", err);
    return null;
  }
}

/**
 * Update classification in Firestore
 */
async function updateClassificationInFirestore(caseId, docId, newCategory, actorId) {
  if (!isFirebaseActive || !firestoreDb) return false;
  try {
    await firestoreDb.collection("cases").doc(caseId)
      .collection("documents").doc(docId).update({
        classification: newCategory,
        class_status: "manual",
        class_confidence: 1.0,
        updated_by: actorId,
        updated_at: firebase.firestore.FieldValue.serverTimestamp()
      });
    return true;
  } catch (err) {
    console.error("[Firebase] Error updating classification in Firestore:", err);
    return false;
  }
}

/**
 * Append tamper-proof audit log entry to Firestore
 */
async function appendAuditToFirestore(auditEntry) {
  if (!isFirebaseActive || !firestoreDb) return false;
  try {
    await firestoreDb.collection("audit_ledger").add({
      actor_id: auditEntry.actor_id,
      action: auditEntry.action,
      resource_id: auditEntry.resource_id,
      outcome: auditEntry.outcome,
      entry_hash: auditEntry.entry_hash,
      prev_hash: auditEntry.prev_hash,
      logged_at: firebase.firestore.FieldValue.serverTimestamp()
    });
    return true;
  } catch (err) {
    console.error("[Firebase] Error appending audit log in Firestore:", err);
    return false;
  }
}
