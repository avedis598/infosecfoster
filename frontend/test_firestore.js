import { initializeApp } from 'firebase/app';
import { getFirestore, doc, getDoc, collection, getDocs } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyC28BR2SSIM7rdF1rKQoFREac8dtS0pGOE",
  authDomain: "infosecfoster-5bb83.firebaseapp.com",
  projectId: "infosecfoster-5bb83",
  storageBucket: "infosecfoster-5bb83.firebasestorage.app",
  messagingSenderId: "97280521197",
  appId: "1:97280521197:web:e7a99bf5fc16851df2ade4",
  measurementId: "G-B4ZZQFWGKF"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

getDocs(collection(db, 'clients')).then(snapshot => {
  snapshot.forEach(doc => {
    console.log("DOC ID:", doc.id);
    console.log("DATA:", doc.data());
  });
  process.exit(0);
});
