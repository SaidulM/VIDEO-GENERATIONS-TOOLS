let storyboard=null;
const $=id=>document.getElementById(id);
async function api(path,body){
 const response=await fetch(path,{method:body?"POST":"GET",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});
 const data=await response.json().catch(()=>({detail:"Invalid server response"}));
 if(!response.ok) throw new Error(data.detail||"Request failed");
 return data;
}
function sceneCard(scene,index){
 const div=document.createElement("div");div.className="scene";
 div.innerHTML='<div class="scenehead"><strong>SCENE '+(index+1)+'</strong><span>'+escapeHtml(scene.role||"story")+'</span></div><label>Narration</label><textarea rows="3" class="narration"></textarea><div class="scenegrid"><div><label>On-screen text</label><textarea rows="2" class="onscreen"></textarea></div><div><label>Visual direction</label><textarea rows="2" class="visual"></textarea></div></div><button class="ghost remove">Remove scene</button>';
 div.querySelector(".narration").value=scene.narration||"";
 div.querySelector(".onscreen").value=scene.on_screen_text||"";
 div.querySelector(".visual").value=scene.visual_prompt||"";
 div.querySelector(".remove").onclick=()=>{div.remove();syncScenes()};
 ["narration","onscreen","visual"].forEach(cls=>div.querySelector("."+cls).addEventListener("input",syncScenes));
 return div;
}
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function syncScenes(){
 if(!storyboard)return;
 const cards=[...$("scenes").querySelectorAll(".scene")];
 storyboard.scenes=cards.map((card,i)=>({id:"scene-"+String(i+1).padStart(2,"0"),role:"story",narration:card.querySelector(".narration").value,on_screen_text:card.querySelector(".onscreen").value,visual_prompt:card.querySelector(".visual").value,duration_hint:5})).filter(s=>s.narration.trim());
 storyboard.full_narration=storyboard.scenes.map(s=>s.narration).join("\n");
 $("renderBtn").disabled=!storyboard.scenes.length;
}
async function refresh(){
 try{
 const data=await api("/api/health");
 $("health").textContent="● Studio online · "+data.providers.filter(p=>p.configured).length+" providers configured";
 $("skillCount").textContent="Skills: "+data.skills.length;
 const current=data.providers.find(p=>p.selected);
 if(current){$("provider").value=current.id;$("model").value=current.model||current.default_model;}
 }catch(e){$("health").textContent="Studio offline: "+e.message;}
}
$("draftBtn").onclick=async()=>{
 $("draftStatus").textContent="Creating storyboard…";$("draftBtn").disabled=true;
 try{
 storyboard=await api("/api/draft",{topic:$("topic").value,script:$("script").value,scene_notes:$("sceneNotes").value,style:$("style").value,language:$("language").value,format:$("format").value});
 $("scenes").innerHTML="";storyboard.scenes.forEach((s,i)=>$("scenes").appendChild(sceneCard(s,i)));
 syncScenes();$("draftStatus").textContent="Ready · "+storyboard.generation_mode;
 }catch(e){$("draftStatus").textContent=e.message;}
 finally{$("draftBtn").disabled=false;}
};
$("addScene").onclick=()=>{
 if(!storyboard){storyboard={title:$("topic").value||"Short Story Speaker",scenes:[],full_narration:""};$("scenes").innerHTML="";}
 const scene={id:"scene-new",role:"story",narration:"",on_screen_text:"",visual_prompt:""};
 $("scenes").appendChild(sceneCard(scene,storyboard.scenes.length));syncScenes();
};
$("previewVoice").onclick=async()=>{
 $("voiceStatus").textContent="Generating voice preview…";
 try{
 const text=storyboard?.full_narration||$("script").value||"Assalamu alaikum. Aaj ki kahani mein ek aham sabaq hai.";
 const result=await api("/api/voice-preview",{text,engine:$("voiceEngine").value,voice_id:$("voiceId").value});
 $("voiceStatus").innerHTML="Preview ready: <audio controls src='"+result.audio_url+"'></audio>";
 }catch(e){$("voiceStatus").textContent=e.message;}
};
$("renderBtn").onclick=async()=>{
 syncScenes();$("renderBtn").disabled=true;$("renderStatus").textContent="Rendering scenes and assembling MP4…";
 try{
 const result=await api("/api/render",{storyboard,style:$("style").value,format:$("format").value,voice_engine:$("voiceEngine").value,voice_id:$("voiceId").value,captions:$("captions").value==="yes",caption_style:$("captionStyle").value,target_seconds:Number($("duration").value)||45,title:storyboard.title});
 $("output").innerHTML='<video class="outputvideo" controls src="'+result.video_url+'"></video><div class="links"><a href="'+result.video_url+'" download>Download MP4</a><a href="'+result.captions_url+'" download>Captions SRT</a><a href="'+result.timestamps_url+'" download>Timestamp JSON</a><a href="'+result.storyboard_url+'" download>Storyboard JSON</a></div>';
 $("renderStatus").textContent="Render complete · "+result.duration_seconds+" sec";
 }catch(e){$("renderStatus").textContent=e.message;}
 finally{$("renderBtn").disabled=!storyboard?.scenes?.length;}
};
$("settingsOpen").onclick=()=>$("settingsDialog").showModal();
$("saveSettings").onclick=async()=>{
 $("settingsStatus").textContent="Saving…";
 try{
 await api("/api/settings",{provider:$("provider").value,api_key:$("apiKey").value,model:$("model").value});
 $("apiKey").value="";$("settingsStatus").textContent="Saved locally. Key hidden.";
 await refresh();
 }catch(e){$("settingsStatus").textContent=e.message;}
};
$("provider").onchange=()=>{
 const defaults={openrouter:"openrouter/free",groq:"llama-3.3-70b-versatile",deepseek:"deepseek-chat",gemini:"gemini-2.5-flash",openai:"gpt-4.1-mini",ollama:"qwen2.5:3b"};
 $("model").value=defaults[$("provider").value]||"";
};
$("voiceEngine").onchange=()=>{
 const chatter=$("voiceEngine").value==="chatterbox";
 $("voiceId").disabled=!chatter&&$("voiceEngine").value==="none";
 if(chatter){$("voiceId").innerHTML='<option value="reference">My permitted reference voice</option>';}
 else if($("voiceEngine").value==="kokoro"){$("voiceId").innerHTML='<option value="hm_omega">Hindi male · Omega</option><option value="hm_psi">Hindi male · Psi</option><option value="hf_alpha">Hindi female · Alpha</option><option value="hf_beta">Hindi female · Beta</option>';}
};
refresh();
