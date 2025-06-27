import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# --- Configuration de la page ---
st.set_page_config(
    page_title="🔐 Détection de Fraude",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS personnalisé pour l'affichage ---
st.markdown("""
<style>
  .main-header { font-size:2.5rem; text-align:center; margin-bottom:2rem; font-weight:bold; }
  .fraud-alert { background:#ff4444; color:#fff; padding:1rem; border-radius:10px; margin:1rem 0; text-align:center; }
  .warning-alert { background:#ffc107; color:#000; padding:1rem; border-radius:10px; margin:1rem 0; text-align:center; }
  .safe-alert { background:#28a745; color:#fff; padding:1rem; border-radius:10px; margin:1rem 0; text-align:center; }
</style>
""", unsafe_allow_html=True)

# --- Saisie de l'URL de l'API dans la barre latérale ---
API_URL = st.sidebar.text_input("🔗 API URL", "http://api_ml:9997")

def api_ok():
    """Teste la disponibilité de l'API."""
    try:
        return requests.get(f"{API_URL}/", timeout=3).status_code == 200
    except:
        return False

# Vérification de l'accessibilité de l'API
if not api_ok():
    st.sidebar.error("❌ API non accessible")
    st.stop()
else:
    info = requests.get(f"{API_URL}/model/info", timeout=3).json()
    st.sidebar.success("✅ API OK")
    st.sidebar.json(info)
    st.sidebar.write(f"🕒 Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}" )

# --- En-tête principal ---
st.markdown('<h1 class="main-header">🛡️ Système de Détection de Fraude IA</h1>', unsafe_allow_html=True)

# --- Onglets principaux ---
tab1, tab2 = st.tabs(["💳 Analyse Transaction", "⚡ Tests Rapides"])

# --- Tab 1: Analyse d'une transaction ---
with tab1:
    st.header("💳 Analyse d'une Transaction")
    with st.form("tx_form"):
        c1, c2 = st.columns(2)
        with c1:
            amount            = st.number_input("💰 Montant (€)", value=100.0, step=0.01)
            card_brand        = st.selectbox("🏷️ Marque", ["VISA", "MASTERCARD", "AMEX"])
            card_type         = st.selectbox("💳 Type", ["Débit", "Crédit"])
            merchant_state    = st.text_input("📍 État marchand", value="CA")
            use_chip          = st.checkbox("🔒 Puce utilisée", value=True)
        with c2:
            credit_limit      = st.number_input("💎 Limite crédit (€)", value=5000.0, step=100.0)
            per_capita_income = st.number_input("👤 Revenu per capita (€)", value=30000.0, step=500.0)
            yearly_income     = st.number_input("💼 Revenu annuel (€)", value=35000.0, step=1000.0)
            total_debt        = st.number_input("💸 Dette totale (€)", value=5000.0, step=500.0)
            credit_score      = st.slider("⭐ Score crédit", 300, 850, 650)
            num_cards         = st.number_input("🔢 Nombre de cartes", min_value=1, max_value=20, value=2)
        submitted = st.form_submit_button("🔍 Analyser")

    # --- Envoi de la transaction à l'API et affichage du résultat ---
    if submitted:
        payload = {
            "amount": float(amount),
            "card_brand": card_brand,
            "card_type": card_type,
            "merchant_state": merchant_state,
            "use_chip": str(use_chip),
            "credit_limit": float(credit_limit),
            "per_capita_income": float(per_capita_income),
            "yearly_income": float(yearly_income),
            "total_debt": float(total_debt),
            "credit_score": float(credit_score),
            "num_credit_cards": int(num_cards),
        }
        with st.spinner("🔄 Analyse en cours..."):
            res = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
        if res.ok:
            r = res.json()
            p = r["fraud_probability"] * 100
            st.metric("🎯 Probabilité de fraude", f"{p:.1f}%")
            st.metric("🔍 Est-ce une fraude ?", "Oui" if r["is_fraud"] else "Non")
            st.metric("📊 Confiance", r["confidence"])

            # Affichage d'une alerte visuelle selon le score
            if p > 70:
                st.markdown(f'<div class="fraud-alert">🚨 {p:.1f}% Probabilité de fraude</div>', unsafe_allow_html=True)
            elif p > 30:
                st.markdown(f'<div class="warning-alert">⚠️ {p:.1f}% Suspecte</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="safe-alert">✅ {p:.1f}% Sûre</div>', unsafe_allow_html=True)
        else:
            st.error(f"❌ API {res.status_code}: {res.text}")

# --- Tab 2: Tests rapides prédéfinis ---
with tab2:
    st.header("⚡ Tests Rapides Prédéfinis")
    st.info("🧪 Testez 3 scénarios types sans saisie manuelle")

    # Trois scénarios de test prédéfinis
    normal = {
        "amount": 5000.0, "card_brand": "AMEX", "card_type": "Crédit", "merchant_state": "TX",
        "use_chip": "False", "credit_limit": 1000.0, "per_capita_income": 10000.0,
        "yearly_income": 15000.0, "total_debt": 14000.0, "credit_score": 450.0, "num_credit_cards": 5
    }
    suspect = {
        "amount": 500.0, "card_brand": "MASTERCARD", "card_type": "Crédit", "merchant_state": "NY",
        "use_chip": "True", "credit_limit": 3000.0, "per_capita_income": 25000.0,
        "yearly_income": 30000.0, "total_debt": 8000.0, "credit_score": 620.0, "num_credit_cards": 3
    }
    fraud = {
        "amount": 50.0, "card_brand": "VISA", "card_type": "Débit", "merchant_state": "CA",
        "use_chip": "True", "credit_limit": 5000.0, "per_capita_income": 30000.0,
        "yearly_income": 40000.0, "total_debt": 2000.0, "credit_score": 800.0, "num_credit_cards": 1
    }

    c1, c2, c3 = st.columns(3)
    if c1.button("✅ Cas Normal"):
        res = requests.post(f"{API_URL}/predict", json=normal, timeout=5)
        st.json(res.json() if res.ok else {"error": res.text})
    if c2.button("⚠️ Cas Suspect"):
        res = requests.post(f"{API_URL}/predict", json=suspect, timeout=5)
        st.json(res.json() if res.ok else {"error": res.text})
    if c3.button("🚨 Cas Frauduleux"):
        res = requests.post(f"{API_URL}/predict", json=fraud, timeout=5)
        st.json(res.json() if res.ok else {"error": res.text})

# --- Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#666;'>🚀 Système IA de Détection de Fraude | FastAPI + Streamlit</div>",
    unsafe_allow_html=True
)
