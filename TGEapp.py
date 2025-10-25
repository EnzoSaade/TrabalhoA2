import streamlit as st
import requests
import pandas as pd
import locale
from datetime import datetime

# --- Configuração e Formatação ---

# Define a localização para formatação monetária (Brasil)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    pass # Ignora se não conseguir configurar (comum em alguns ambientes online)

def formatar_moeda(valor):
    """Formata um valor numérico para o padrão monetário BRL (R$)"""
    try:
        # Tenta usar o locale
        return locale.currency(valor, grouping=True)
    except:
        # Retorna formatação manual se o locale falhar
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Funções de API ---

@st.cache_data(ttl=3600)
def buscar_deputados(nome):
    """Busca deputados por nome na API da Câmara"""
    if not nome:
        return []
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    params = {"nome": nome, "ordem": "ASC", "ordenarPor": "nome"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("dados", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Erro na conexão ao buscar deputados: {e}")
        return None

@st.cache_data(ttl=3600)
def obter_despesas_deputado(id_deputado, ano, mes=None, limite=1000):
    """Obtém as despesas do deputado"""
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/despesas"
    
    params = {
        "ano": ano,
        "ordem": "DESC",
        "ordenarPor": "dataDocumento",
        "itens": limite
    }

    if mes and 1 <= mes <= 12:
        params["mes"] = mes

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("dados", [])
    except requests.exceptions.RequestException:
        return None

def calcular_total_despesas(despesas):
    """Calcula o total das despesas e retorna o DataFrame processado."""
    if not despesas:
        return 0, pd.DataFrame()
    
    df = pd.DataFrame(despesas)
    # Converte para numérico, tratando erros e NaN
    df['valorDocumento'] = pd.to_numeric(df['valorDocumento'], errors='coerce').fillna(0)
    total = df['valorDocumento'].sum()
    
    return total, df

# --- Função Principal de Comparação ---

def comparar_deputados_ui():
    
    st.title("⚖️ Comparação de Despesas entre Deputados Federais")
    
    # FRASE ALTERADA AQUI
    st.markdown("POR UMA ATIVIDADE PARLAMENTAR MAIS TRANSPARENTE E REPUBLICANA! 🇧🇷")
    
    # --- 1. Seleção de Deputados ---
    col_dep1, col_dep2 = st.columns(2)
    
    deputado_selecionado1 = None
    deputado_selecionado2 = None

    with col_dep1:
        st.subheader("Deputado 1")
        nome1 = st.text_input("Nome do 1º Deputado (Busca)", key="nome1")
        
        if nome1:
            deputados1 = buscar_deputados(nome1)
            if deputados1:
                opcoes1 = {f"{d['nome']} ({d['siglaPartido']}/{d['siglaUf']})": d for d in deputados1}
                escolha1 = st.selectbox("Selecione o deputado exato", options=list(opcoes1.keys()), key="select1")
                deputado_selecionado1 = opcoes1.get(escolha1)
            else:
                st.info("Nenhum deputado encontrado.")

    with col_dep2:
        st.subheader("Deputado 2")
        nome2 = st.text_input("Nome do 2º Deputado (Busca)", key="nome2")
        
        if nome2:
            deputados2 = buscar_deputados(nome2)
            if deputados2:
                opcoes2 = {f"{d['nome']} ({d['siglaPartido']}/{d['siglaUf']})": d for d in deputados2}
                escolha2 = st.selectbox("Selecione o deputado exato", options=list(opcoes2.keys()), key="select2")
                deputado_selecionado2 = opcoes2.get(escolha2)
            else:
                st.info("Nenhum deputado encontrado.")

    # Verifica se a comparação pode prosseguir
    if not deputado_selecionado1 or not deputado_selecionado2:
        st.warning("Aguardando a seleção de dois deputados.")
        return
    
    if deputado_selecionado1['id'] == deputado_selecionado2['id']:
        st.error("⚠️ Você selecionou o mesmo deputado duas vezes. Selecione dois diferentes.")
        return
        
    st.markdown("---")
        
    # --- 2. Seleção do Período ---
    st.subheader("🗓️ Período para Comparação")
    
    ano_padrao = datetime.now().year
    anos_disponiveis = list(range(ano_padrao, ano_padrao - 5, -1))
    
    col_c_ano, col_c_mes = st.columns(2)
    
    ano = col_c_ano.selectbox("Ano", options=anos_disponiveis, key="comp_ano")
    
    meses_comp = {
        None: "Todo o Ano", 1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro",
        10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    mes_nome = col_c_mes.selectbox("Mês", options=list(meses_comp.values()), key="comp_mes")
    mes = [k for k, v in meses_comp.items() if v == mes_nome][0]

    # --- 3. Busca de Dados e Processamento ---
    
    with st.spinner("⏳ Carregando despesas..."):
        despesas1_raw = obter_despesas_deputado(deputado_selecionado1['id'], ano=ano, mes=mes)
        despesas2_raw = obter_despesas_deputado(deputado_selecionado2['id'], ano=ano, mes=mes)
    
    if despesas1_raw is None or despesas2_raw is None:
        st.error("❌ Erro ao carregar as despesas. Verifique a conexão com a API.")
        return

    total1, df1 = calcular_total_despesas(despesas1_raw)
    total2, df2 = calcular_total_despesas(despesas2_raw)

    # --- 4. Exibição da Comparação ---
    st.markdown("## 📊 Resultado")
    
    col_res1, col_res2 = st.columns(2)
    
    # Total Deputado 1
    with col_res1:
        st.info(f"👤 **{deputado_selecionado1['nome']}** ({deputado_selecionado1['siglaPartido']}/{deputado_selecionado1['siglaUf']})")
        st.metric("Total de Despesas", formatar_moeda(total1))
        st.caption(f"Registros: {len(df1)}")

    # Total Deputado 2
    with col_res2:
        st.info(f"👤 **{deputado_selecionado2['nome']}** ({deputado_selecionado2['siglaPartido']}/{deputado_selecionado2['siglaUf']})")
        st.metric("Total de Despesas", formatar_moeda(total2))
        st.caption(f"Registros: {len(df2)}")

    st.markdown("### Análise")
    diferenca = abs(total1 - total2)
    
    if total1 > total2:
        vencedor = deputado_selecionado1
        perdedor = deputado_selecionado2
        percentual = ((total1 - total2) / total2 * 100) if total2 > 0 else "N/A"
        msg = f"**{vencedor['nome']}** gastou **{formatar_moeda(diferenca)}** a mais que {perdedor['nome']}"
        if total2 > 0:
             msg += f" (Representa **{percentual:.1f}%** a mais)."
        st.success(f"📈 {msg}")
    elif total2 > total1:
        vencedor = deputado_selecionado2
        perdedor = deputado_selecionado1
        percentual = ((total2 - total1) / total1 * 100) if total1 > 0 else "N/A"
        msg = f"**{vencedor['nome']}** gastou **{formatar_moeda(diferenca)}** a mais que {perdedor['nome']}"
        if total1 > 0:
             msg += f" (Representa **{percentual:.1f}%** a mais)."
        st.error(f"📉 {msg}")
    else:
        st.info("Ambos os deputados tiveram o mesmo total de despesas no período.")

    # --- 5. Detalhamento em Tabela ---
    st.markdown("### Detalhamento das Despesas (Registros)")
    
    col_tab1, col_tab2 = st.columns(2)

    def display_dataframe(df, nome_deputado, col):
        if df.empty:
            col.info(f"Nenhuma despesa para {nome_deputado}.")
            return
            
        df_exibicao = df[['dataDocumento', 'tipoDespesa', 'nomeFornecedor', 'valorDocumento']].copy()
        df_exibicao.rename(columns={
            'dataDocumento': 'Data', 
            'tipoDespesa': 'Tipo de Despesa', 
            'nomeFornecedor': 'Fornecedor', 
            'valorDocumento': 'Valor (R$)'
        }, inplace=True)
        
        # Formatação final de moeda
        df_exibicao['Valor (R$)'] = df_exibicao['Valor (R$)'].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        col.subheader(nome_deputado)
        col.dataframe(df_exibicao, use_container_width=True)

    with col_tab1:
        display_dataframe(df1, deputado_selecionado1['nome'], col_tab1)

    with col_tab2:
        display_dataframe(df2, deputado_selecionado2['nome'], col_tab2)

# --- Execução do App ---
if __name__ == "__main__":
    st.set_page_config(
        page_title="Comparação de Deputados",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    comparar_deputados_ui()
