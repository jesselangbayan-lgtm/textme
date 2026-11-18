# app_v3.py - TextMe v3: ONLINE + Profile Pics + Seen Ticks
# FEATURES: 1:1 + Group Chat, Real OTP via Semaphore, Online Deploy, Avatars, Seen ✓✓
# RUN LOCALLY: pip install flask flask-socketio requests ; python app_v3.py
# RUN ONLINE: See DEPLOY guide at bottom of this file / in chat

import os, random, requests, base64
from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SEMAPHORE_API_KEY = os.environ.get("SEMAPHORE_API_KEY", "PASTE_YOUR_SEMAPHORE_API_KEY_HERE")
SEMAPHORE_SENDER = os.environ.get("SEMAPHORE_SENDER", "SEMAPHORE")

users = {} # number -> {otp, verified, name, avatar (base64 or emoji), online}
messages = {} # number -> [msg]
groups = {} # gid -> {name, members, messages, avatar}
# msg = {id, from, to/group_id, text, sender_name, sender_avatar, status: sent/delivered/seen, time}

def send_real_sms(to_number, text):
    if not SEMAPHORE_API_KEY or SEMAPHORE_API_KEY=="PASTE_YOUR_SEMAPHORE_API_KEY_HERE":
        print(f"[DEMO OTP] {to_number} -> {text}"); return False
    try:
        num=to_number.strip()
        if num.startswith("+63"): num="0"+num[3:]
        elif num.startswith("63"): num="0"+num[2:]
        r=requests.post("https://api.semaphore.co/api/v4/messages",
            data={"apikey":SEMAPHORE_API_KEY,"number":num,"message":text,"sender_name":SEMAPHORE_SENDER}, timeout=10)
        print(f"[SEMAPHORE] {num} {r.status_code}"); return r.status_code==200
    except Exception as e: print(e); return False

HTML = r"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TextMe v3 - Online Messenger</title>
<style>
*{box-sizing:border-box;font-family:system-ui} body{margin:0;background:#0f172a;color:#fff}
.wrap{max-width:560px;margin:0 auto;height:100dvh;display:flex;flex-direction:column;background:#111827}
header{padding:12px 14px;background:#1e293b;display:flex;gap:10px;align-items:center}
header img{width:40px;height:40px;border-radius:50%;object-fit:cover;background:#374151}
header b{font-size:17px} header span{font-size:11px;color:#22c55e}
.card{padding:20px} input,button{width:100%;padding:12px;border-radius:12px;border:none;margin-top:10px;font-size:15px}
input{background:#1f2937;color:#fff;outline:none} button{background:#22c55e;color:#000;font-weight:700;cursor:pointer}
.small{font-size:13px;color:#94a3b8;margin-top:8px;text-align:center}
.avatar-picker{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap} .avatar-picker span{font-size:28px;cursor:pointer;padding:6px;border-radius:50%;background:#1f2937} .avatar-picker span.sel{outline:2px solid #22c55e}
.tabs{display:flex;gap:8px;padding:10px;background:#1e293b} .tabs button{margin:0;background:#374151;color:#fff} .tabs button.active{background:#22c55e;color:#000}
#chat{display:none;flex-direction:column;height:100%}
#toBar{padding:10px;background:#1e293b} #toBar input{margin:0}
#msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:8px;max-width:88%} .row.me{align-self:flex-end;flex-direction:row-reverse} .row.other{align-self:flex-start}
.row img{width:32px;height:32px;border-radius:50%;object-fit:cover;background:#374151;flex-shrink:0}
.bubble{padding:9px 12px;border-radius:14px;font-size:15px;line-height:1.4;max-width:100%} .me .bubble{background:#22c55e;color:#000;border-bottom-right-radius:4px} .other .bubble{background:#374151;border-bottom-left-radius:4px}
.meta{font-size:11px;opacity:.75;margin-bottom:2px} .ticks{font-size:11px;text-align:right;margin-top:2px;opacity:.9} .ticks.seen{color:#60a5fa;font-weight:700} .ticks.delivered{color:#e5e7eb}
#sendBar{padding:12px;display:flex;gap:8px;background:#1e293b} #sendBar input{margin:0;flex:1} #sendBar button{width:80px;margin:0}
.group-item{background:#1f2937;padding:10px 12px;border-radius:10px;margin-top:8px;cursor:pointer;display:flex;justify-content:space-between;align-items:center}
.group-item img{width:36px;height:36px;border-radius:50%;object-fit:cover}
.online-dot{width:10px;height:10px;background:#22c55e;border-radius:50%;display:inline-block}
</style></head>
<body><div class="wrap">
<header><span id="myAvatarHead" style="font-size:32px">💬</span><div style="flex:1"><b>TextMe v3</b><br><span>● Online • WiFi/Data • No Load for chat</span></div><span id="onlineCount"></span></header>

<div id="login" class="card">
  <h2 style="margin:0">Login with SIM Number</h2>
  <p class="small" style="text-align:left">Pick your profile pic, get REAL OTP via Semaphore, then chat anywhere - even if laptop is off (when deployed online).</p>
  <input id="myNum" placeholder="09171234567 or +639171234567">
  <input id="myName" placeholder="Your Name (e.g. Jesse)">
  <label class="small" style="text-align:left;display:block">Choose avatar:</label>
  <div class="avatar-picker" id="avatarPicker">
    <span onclick="pickAvatar('😀',this)" class="sel">😀</span><span onclick="pickAvatar('😎',this)">😎</span><span onclick="pickAvatar('🔥',this)">🔥</span><span onclick="pickAvatar('🐱',this)">🐱</span><span onclick="pickAvatar('🐶',this)">🐶</span><span onclick="pickAvatar('👑',this)">👑</span><span onclick="pickAvatar('🌸',this)">🌸</span><span onclick="pickAvatar('⚽',this)">⚽</span>
  </div>
  <label class="small" style="text-align:left;display:block">Or upload photo:</label>
  <input type="file" id="avatarFile" accept="image/*" onchange="uploadAvatar(event)">
  <div id="avatarPreview" class="small"></div>
  <button onclick="register()">Send REAL OTP via SMS</button>
  <input id="otp" placeholder="Enter 6-digit OTP" style="display:none">
  <button id="otpBtn" onclick="verify()" style="display:none;background:#3b82f6;color:#fff">Verify & Enter Chat</button>
  <p id="otpHint" class="small"></p>
</div>

<div id="chat">
  <div class="tabs"><button id="tab1" class="active" onclick="showTab('dm')">1:1 Chat</button><button id="tab2" onclick="showTab('group')">Group Chat</button></div>
  <div id="dmTab"><div id="toBar"><input id="toNum" placeholder="Chat with number: 0917..."></div><div style="padding:0 10px"><button onclick="loadDM()" style="background:#3b82f6;color:#fff">Start 1:1 Chat</button></div></div>
  <div id="groupTab" style="display:none;padding:12px"><b>Create Group</b><input id="gName" placeholder="Group name e.g. Family, Barkada"><input id="gMembers" placeholder="Members: 0917...,0918..."><button onclick="createGroup()">Create Group</button><div id="groupList"></div></div>
  <div id="msgs"><p class="small">Select a chat to start.</p></div>
  <div id="sendBar"><input id="msgInput" placeholder="Type message..."><button onclick="sendMsg()">Send</button></div>
</div>
</div>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
let myNum="",myName="",myAvatar="😀",socket=null,mode="dm",currentTo="",currentGroup="";
function pickAvatar(e,el){myAvatar=e;document.querySelectorAll('.avatar-picker span').forEach(s=>s.classList.remove('sel'));el.classList.add('sel');}
function uploadAvatar(ev){let f=ev.target.files[0];if(!f)return;let r=new FileReader();r.onload=()=>{myAvatar=r.result;document.getElementById('avatarPreview').innerHTML='<img src="'+myAvatar+'" style="width:60px;height:60px;border-radius:50%;object-fit:cover">';};r.readAsDataURL(f);}
function showTab(t){document.getElementById('tab1').classList.toggle('active',t==='dm');document.getElementById('tab2').classList.toggle('active',t==='group');document.getElementById('dmTab').style.display=t==='dm'?'block':'none';document.getElementById('groupTab').style.display=t==='group'?'block':'none';mode=t;}
async function register(){myNum=document.getElementById('myNum').value.trim();myName=document.getElementById('myName').value.trim()||"User";if(!myNum){alert("Enter SIM number");return;}let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({number:myNum,name:myName,avatar:myAvatar})});let d=await r.json();document.getElementById('otp').style.display='block';document.getElementById('otpBtn').style.display='block';document.getElementById('otpHint').innerHTML=d.real_sms?"✅ Real OTP sent via SMS to "+myNum:"⚠️ No Semaphore key - Demo OTP: <b style='color:#fff'>"+d.demo_otp+"</b>";if(d.real_sms)alert("OTP sent to "+myNum);}
async function verify(){let otp=document.getElementById('otp').value.trim();let r=await fetch('/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({number:myNum,otp:otp})});let d=await r.json();if(d.status!=='verified'){alert("Wrong OTP");return;}document.getElementById('login').style.display='none';document.getElementById('chat').style.display='flex';document.getElementById('myAvatarHead').innerHTML=myAvatar.startsWith('data:')?'<img src="'+myAvatar+'" style="width:40px;height:40px;border-radius:50%;object-fit:cover">':myAvatar;socket=io();socket.on('connect',()=>{socket.emit('join',{number:myNum,name:myName,avatar:myAvatar})});socket.on('receive_message',(m)=>{if(mode==='dm'&&(m.from===currentTo||m.to===currentTo)){addBubble(m); if(m.from===currentTo) markSeen(m.id);} updateTicks(m);});socket.on('receive_group_message',(m)=>{if(mode==='group'&&m.group_id===currentGroup) addBubble(m,true);});socket.on('history',(list)=>{document.getElementById('msgs').innerHTML='';list.forEach(m=>{addBubble(m); if(m.from!==myNum) markSeen(m.id);});});socket.on('group_history',(list)=>{document.getElementById('msgs').innerHTML='';list.forEach(m=>addBubble(m,true));});socket.on('my_groups',(list)=>{renderGroups(list)});socket.on('message_status',(d)=>{let el=document.getElementById('ticks-'+d.id);if(el){el.textContent=d.status==='seen'?'✓✓ Seen':d.status==='delivered'?'✓✓ Delivered':'✓ Sent';el.className='ticks '+(d.status==='seen'?'seen':'delivered');}});socket.emit('list_groups',{number:myNum});}
function markSeen(id){socket.emit('mark_seen',{id:id, by:myNum});}
function updateTicks(m){} // ticks updated via message_status
function renderAvatar(av){return av&&av.startsWith('data:')?'<img src="'+av+'">':'<span style="font-size:28px">'+(av||'😀')+'</span>';}
function addBubble(m,isGroup){let isMe=m.from===myNum;let div=document.createElement('div');div.className='row '+(isMe?'me':'other');let ticks='';if(isMe){let t=m.status==='seen'?'✓✓ Seen':m.status==='delivered'?'✓✓ Delivered':'✓ Sent';ticks='<div class="ticks '+(m.status==='seen'?'seen':'delivered')+'" id="ticks-'+m.id+'">'+t+'</div>';}div.innerHTML='<div>'+renderAvatar(m.sender_avatar)+'</div><div style="flex:1"><div class="meta">'+(isMe?'You':(m.sender_name||m.from))+'</div><div class="bubble">'+m.text+'</div>'+ticks+'</div>';document.getElementById('msgs').appendChild(div);document.getElementById('msgs').scrollTop=99999;}
function renderGroups(list){let el=document.getElementById('groupList');el.innerHTML='<b style="display:block;margin-top:14px">Your Groups</b>';if(!list.length)el.innerHTML+='<p class="small">No groups yet.</p>';list.forEach(g=>{let d=document.createElement('div');d.className='group-item';d.innerHTML='<span>👥 '+g.name+' <small>('+g.members.length+')</small></span><span>Open →</span>';d.onclick=()=>openGroup(g.id,g.name);el.appendChild(d);});}
async function createGroup(){let name=document.getElementById('gName').value.trim();let members=document.getElementById('gMembers').value.split(',').map(s=>s.trim()).filter(Boolean);if(!name||!members.length){alert("Enter group name + member");return;}if(!members.includes(myNum))members.push(myNum);let r=await fetch('/create_group',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,members:members,creator:myNum})});let d=await r.json();alert("Group created!");socket.emit('list_groups',{number:myNum});openGroup(d.group_id,name);}
function loadDM(){currentTo=document.getElementById('toNum').value.trim();mode='dm';showTab('dm');if(!currentTo){alert("Enter receiver number");return;}document.getElementById('msgs').innerHTML='<p class="small">Chatting with '+currentTo+'</p>';socket.emit('get_history',{number:myNum,with:currentTo});}
function openGroup(id,name){currentGroup=id;mode='group';showTab('group');document.getElementById('msgs').innerHTML='<p class="small">👥 Group: '+name+'</p>';socket.emit('join_group',{group_id:id,number:myNum});socket.emit('get_group_history',{group_id:id});}
function sendMsg(){let txt=document.getElementById('msgInput').value.trim();if(!txt)return;if(mode==='dm'){if(!currentTo){alert("Select 1:1 first");return;}let m={from:myNum,to:currentTo,text:txt,sender_name:myName,sender_avatar:myAvatar};socket.emit('send_message',m);}else{if(!currentGroup){alert("Open group first");return;}socket.emit('send_group_message',{group_id:currentGroup,from:myNum,sender_name:myName,sender_avatar:myAvatar,text:txt});}document.getElementById('msgInput').value='';}
document.getElementById('msgInput')?.addEventListener('keydown',e=>{if(e.key==='Enter')sendMsg()});
</script></body></html>
"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/health')
def health(): return jsonify({"status":"online","users":len(users),"groups":len(groups)})

@app.route('/register', methods=['POST'])
def register():
    d=request.json; num=d.get('number'); otp=str(random.randint(100000,999999))
    users[num]={'otp':otp,'verified':False,'name':d.get('name','User'),'avatar':d.get('avatar','😀'),'online':False}
    sent=send_real_sms(num, f"Your TextMe OTP is {otp}. Do not share it.")
    return jsonify({"status":"otp_sent","real_sms":sent,"demo_otp": otp if not sent else "****"})
@app.route('/verify', methods=['POST'])
def verify():
    d=request.json; num=d.get('number')
    if users.get(num,{}).get('otp')==d.get('otp'):
        users[num]['verified']=True; return jsonify({"status":"verified"})
    return jsonify({"status":"wrong_otp"}),400
@app.route('/create_group', methods=['POST'])
def create_group():
    d=request.json; gid=f"g{random.randint(1000,9999)}"
    groups[gid]={'name':d.get('name'),'members':d.get('members',[]),'messages':[]}
    return jsonify({"status":"created","group_id":gid})

@socketio.on('join')
def on_join(data):
    num=data['number']
    if num in users: users[num].update({'name':data.get('name',users[num]['name']),'avatar':data.get('avatar',users[num]['avatar']),'online':True})
    join_room(num)
    # mark pending messages as delivered
    for m in messages.get(num,[]):
        if m['from']!=num and m.get('status')=='sent':
            m['status']='delivered'; emit('message_status',{'id':m['id'],'status':'delivered'},room=m['from'])

@socketio.on('send_message')
def handle(data):
    mid=f"m{random.randint(100000,999999)}"
    msg={"id":mid,"from":data['from'],"to":data['to'],"text":data['text'],"sender_name":data.get('sender_name',''),"sender_avatar":data.get('sender_avatar','😀'),"status":"sent"}
    # delivered if receiver online
    if users.get(data['to'],{}).get('online'): msg['status']='delivered'
    messages.setdefault(data['to'],[]).append(msg); messages.setdefault(data['from'],[]).append(msg)
    emit('receive_message',msg,room=data['to'])
    emit('message_status',{'id':mid,'status':msg['status']},room=data['from'])
    print(f"DM {msg['from']}->{msg['to']}: {msg['text']} [{msg['status']}]")

@socketio.on('get_history')
def history(data):
    num=data['number']; other=data.get('with','')
    emit('history',[m for m in messages.get(num,[]) if m['from']==other or m['to']==other])

@socketio.on('mark_seen')
def mark_seen(data):
    mid=data['id']; by=data['by']
    # find msg in any user's list and mark seen
    for lst in messages.values():
        for m in lst:
            if m['id']==mid and m['from']!=by:
                m['status']='seen'; emit('message_status',{'id':mid,'status':'seen'},room=m['from']); return

@socketio.on('join_group')
def join_group(data): join_room(data['group_id'])
@socketio.on('send_group_message')
def group_msg(data):
    gid=data['group_id']; mid=f"m{random.randint(100000,999999)}"
    msg={"id":mid,"from":data['from'],"sender_name":data.get('sender_name',''),"sender_avatar":data.get('sender_avatar','😀'),"text":data['text'],"group_id":gid,"status":"delivered"}
    if gid in groups: groups[gid]['messages'].append(msg); emit('receive_group_message',msg,room=gid)
@socketio.on('get_group_history')
def gh(data): emit('group_history', groups.get(data['group_id'],{}).get('messages',[]))
@socketio.on('list_groups')
def lg(data):
    num=data['number']; emit('my_groups',[{"id":gid,"name":g['name'],"members":g['members']} for gid,g in groups.items() if num in g['members']])

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000))
    print(f"Running on port {port} - Online ready")
    socketio.run(app, host='0.0.0.0', port=port)
