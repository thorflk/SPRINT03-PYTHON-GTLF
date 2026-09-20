# Diagramas de arquitetura e integração

Diagramas em [Mermaid](https://mermaid.js.org/), renderizados automaticamente pelo GitHub.

## 1. Blocos: as três camadas da Sprint 1 no protótipo

```mermaid
flowchart TB
  subgraph DIG["Camada digital (Python, este repositório)"]
    DEM["Controle de demanda<br/>demanda.py"]
    TAR["Tarifação<br/>tarifacao.py"]
    IA["Previsão de pico<br/>previsao.py"]
    DASH["Dashboard e relatórios<br/>relatorio.py / graficos.py"]
  end
  subgraph CON["Camada de conectividade (simulada)"]
    OCPP["Mensagens OCPP 1.6J<br/>ocpp.py"]
    MOD["Leitura tipo MODBUS<br/>medidor.py"]
  end
  subgraph FIS["Camada física (simulada)"]
    PV["Usina solar GoodWe<br/>solar.py"]
    HCA["4 carregadores HCA G2<br/>sessoes.py"]
    EV["Veículos elétricos<br/>veiculos.py"]
  end
  FIS --> CON
  CON --> DIG
  DIG -.->|SetChargingProfile| CON
  CON -.-> FIS
```

## 2. Esquema elétrico unifilar simplificado

```mermaid
flowchart LR
  REDE["Rede da concessionária<br/>30 kW disponíveis"] --> MG["Medidor geral"]
  MG --> QD["Quadro de distribuição"]
  PV["Módulos fotovoltaicos<br/>15 kWp"] --> INV["Inversor GoodWe"]
  INV --> QD
  QD --> C1["HCA G2 - P1<br/>7,4 kW"]
  QD --> C2["HCA G2 - P2<br/>11 kW"]
  QD --> C3["HCA G2 - P3<br/>22 kW"]
  QD --> C4["HCA G2 - P4<br/>7,4 kW"]
  C1 -.->|OCPP e medição| CTRL["Controlador Python<br/>controle de demanda"]
  C2 -.-> CTRL
  C3 -.-> CTRL
  C4 -.-> CTRL
  CTRL -.->|limite de potência| C1
  CTRL -.-> C2
  CTRL -.-> C3
  CTRL -.-> C4
```

## 3. Fluxograma do laço de simulação (um intervalo de 5 min)

```mermaid
flowchart TD
  A["Início do intervalo"] --> B["Chegadas e saídas de sessões<br/>StartTransaction / StopTransaction"]
  B --> C["Potência desejada por ponto<br/>min(nominal, OBC, curva por SoC)"]
  C --> D["Geração solar do intervalo"]
  D --> E{"Demanda desejada maior<br/>que limite + solar?"}
  E -- sim --> F["Fator proporcional<br/>SetChargingProfile"]
  E -- não --> G["Alocada = desejada"]
  F --> H["Energia entregue e SoC"]
  G --> H
  H --> I["Origem: solar primeiro, resto da rede"]
  I --> J["Tarifa da faixa horária e custo"]
  J --> K["MeterValues e telemetria"]
  K --> L{"Último intervalo do dia?"}
  L -- não --> A
  L -- sim --> M["Relatórios, gráficos e previsão"]
```

## 4. Sequência de uma sessão de recarga

```mermaid
sequenceDiagram
  participant EV as Veículo
  participant CP as HCA G2 (ponto)
  participant CS as Controlador Python
  participant DEM as Controle de demanda
  participant TAR as Tarifação
  EV->>CP: conecta e autoriza (RFID)
  CP->>CS: StartTransaction
  loop a cada 5 min
    CS->>DEM: potências desejadas + geração solar
    DEM-->>CS: potências alocadas
    CS-->>CP: SetChargingProfile (só se houver corte)
    CP->>CS: MeterValues (W e Wh)
    CS->>TAR: energia do intervalo
    TAR-->>CS: custo em Decimal
  end
  CP->>CS: StopTransaction
  CS-->>EV: recibo (kWh, parcela solar, R$)
```
