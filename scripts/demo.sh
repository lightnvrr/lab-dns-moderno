#!/usr/bin/env bash
# Roteiro da demonstração, pensado para a gravação do vídeo.
# Rode dentro do cliente-a:  bash /lab/scripts/demo.sh
# Cada etapa mostra o comando, roda e espera Enter.
# Para repetir a demo do zero: docker compose restart borda resolvedor

LAB="${LAB:-/lab}"
B="${BORDA:-172.21.0.53}"      # a borda, vista pela rede do cliente-a
IFACE="${IFACE:-eth0}"

titulo() { printf '\n\033[1;35m==== %s ====\033[0m\n\n' "$1"; }
cmd()    { printf '\033[1;33m$ %s\033[0m\n' "$1"; bash -c "$1"; echo; }
pausa()  { read -rp $'\033[2m(Enter para continuar)\033[0m ' _; }

titulo "1. DNSSEC: resposta assinada e validada"
cmd "dig @$B www.lab.internal +dnssec +noall +comments +answer | grep -E 'flags|status|IN'"
echo "Repare na flag 'ad' (dado autenticado) e no RRSIG junto do registro A."
pausa

titulo "2. Um atacante altera a resposta"
cmd "bash $LAB/scripts/quebrar_zona.sh"
echo "Aguardando o autoritativo recarregar a zona..."; sleep 7
cmd "dig @$B banco.lab.internal +dnssec +noall +comments +answer | grep -E 'status|IN'"
echo "SERVFAIL: o resolvedor conferiu a assinatura, ela não bate, e a resposta foi descartada."
pausa
cmd "dig @$B banco.lab.internal +cd +noall +answer"
echo "Com +cd (sem validação) o IP falso 10.6.6.6 aparece: o dado chegou, quem barrou foi o DNSSEC."
pausa

titulo "3. Desfazendo a quebra"
cmd "bash $LAB/scripts/restaurar_zona.sh"
pausa

titulo "4. Privacidade: o mesmo pedido por UDP, DoT e DoH"
for proto in do53 dot doh; do
    case $proto in
        do53) porta=53;  opt="";;
        dot)  porta=853; opt="+tls";;
        doh)  porta=443; opt="+https";;
    esac
    tcpdump -i "$IFACE" -w "$LAB/capturas/$proto.pcap" "port $porta" >/dev/null 2>&1 &
    PID=$!; sleep 1
    cmd "dig @$B $opt www.lab.internal +short"
    sleep 1; kill $PID 2>/dev/null; wait $PID 2>/dev/null
done
echo "Capturas salvas em capturas/. O que um observador da rede vê em cada uma:"
cmd "tcpdump -nr $LAB/capturas/do53.pcap 2>/dev/null"
echo "No DNS comum, o nome www.lab.internal e a resposta aparecem em texto puro."
pausa
cmd "tcpdump -nr $LAB/capturas/dot.pcap 2>/dev/null | head -12"
echo "No DoT só aparecem pacotes TCP na porta 853, com conteúdo cifrado. Nenhum nome."
pausa
cmd "tcpdump -nr $LAB/capturas/doh.pcap 2>/dev/null | head -12"
echo "No DoH é igual, mas na porta 443: parece navegação comum."
pausa

titulo "5. Envenenamento de cache: a conta"
cmd "python3 $LAB/medicao/chance_envenenamento.py"
pausa

titulo "6. DNS protetivo"
cmd "dig @$B doubleclick.net +short"
echo "Bloqueado: a borda devolve 0.0.0.0."
cmd "dig @$B +https malware.lab.internal +short"
echo "O bloqueio vale também para DoT e DoH."
cmd "dig @1.1.1.1 doubleclick.net +short +time=3 +tries=1 | head -3"
echo "Perguntando direto a outro resolvedor, o bloqueio não vale. É o limite do DNS protetivo."
cmd "dig @$B use-application-dns.net +noall +comments | grep status"
echo "Domínio canário do Firefox respondendo NXDOMAIN."
pausa

titulo "7. GeoDNS"
cmd "dig @$B cdn.geo.internal +short"
echo "Do cliente-a (região A) a resposta é 10.1.0.10."
echo "No outro terminal: docker compose exec cliente-b dig @172.22.0.53 cdn.geo.internal +short  (10.2.0.10)"
pausa

titulo "8. Anycast: qual data center respondeu?"
cmd "dig @1.1.1.1 id.server CH TXT +short +time=3 +tries=1"
cmd "dig @9.9.9.9 id.server CH TXT +short +time=3 +tries=1"
echo "O mesmo IP é anunciado por vários data centers; a rede leva você ao mais próximo."

titulo "Fim da demonstração"
