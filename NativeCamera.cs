using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using System.Globalization;
using ValveResourceFormat;
using ValveResourceFormat.ResourceTypes;
using ValveKeyValue;
public static class PatchModels {
 static bool CameraName(string n) => Regex.IsMatch(n,@"^(near|far|gunaim)_\d+$");
 static bool AttachmentName(string n) => n=="standing_pivot" || n=="crouching_pivot" || CameraName(n);
 static KVObject ParseRoot(string text,string template) {
  if(!string.IsNullOrWhiteSpace(text))return Parse(text).Root;
  int i=template.IndexOf("\n{");if(i<0)throw new Exception("Missing native model metadata header");
  return Parse(template.Substring(0,i)+"\n{\n}\n").Root;
 }
 static string NodeText(string text,string key){
  var m=Regex.Match(text,@"\b"+Regex.Escape(key)+@"\s*=\s*[\[{]");if(!m.Success)return null;
  int start=m.Index+m.Length-1,end=start+1,depth=1;char open=text[start],close=open=='{'?'}':']';bool quoted=false,escape=false;
  for(;end<text.Length && depth>0;end++){
   char c=text[end];if(quoted){if(escape)escape=false;else if(c=='\\')escape=true;else if(c=='"')quoted=false;continue;}
   if(c=='"'){quoted=true;continue;}if(c==open)depth++;else if(c==close)depth--;
  }
  if(depth!=0)throw new Exception("Unbalanced metadata node");return text.Substring(m.Index,end-m.Index);
 }
 static string PutNode(string text,string key,string node){
  var old=NodeText(text,key);if(old!=null){int i=text.IndexOf(old,StringComparison.Ordinal);return text.Substring(0,i)+node+text.Substring(i+old.Length);}
  int end=text.LastIndexOf('}');if(end<0)throw new Exception("Invalid model metadata");return text.Insert(end,"\n"+node+"\n");
 }
 static KVDocument Parse(string text){using var s=new MemoryStream(Encoding.UTF8.GetBytes(text));return KVSerializer.Create(KVSerializationFormat.KeyValues3Text).Deserialize(s);}
 static KVObject[] Cameras(KVDocument d,bool selected){
  if(!d.Root.ContainsKey("AttachmentCameraData"))return Array.Empty<KVObject>();
  return d.Root["AttachmentCameraData"].Values.Where(v=>CameraName(v["attachment_name"].ToString())==selected).ToArray();
 }
 static bool Metadata(KVObject data,KVObject original){
  var originalText=original["m_modelInfo"]["m_keyValueText"].ToString();
  if(string.IsNullOrWhiteSpace(originalText))return false;
  var inputText=data["m_modelInfo"]["m_keyValueText"].ToString();
  if(string.IsNullOrWhiteSpace(inputText)){int i=originalText.IndexOf("\n{");if(i<0)throw new Exception("Invalid native metadata");inputText=originalText.Substring(0,i)+"\n{\n}\n";}
  var a=Parse(inputText);var b=Parse(originalText);
  bool settingsChanged=false;
  if(b.Root.ContainsKey("CitadelCameraSettings_t")){
   bool same=a.Root.ContainsKey("CitadelCameraSettings_t");
   if(same){try{Equal(a.Root["CitadelCameraSettings_t"],b.Root["CitadelCameraSettings_t"]);}catch{same=false;}}
   if(!same){inputText=PutNode(inputText,"CitadelCameraSettings_t",NodeText(originalText,"CitadelCameraSettings_t"));settingsChanged=true;}
  }else if(a.Root.ContainsKey("CitadelCameraSettings_t")){
   var node=NodeText(inputText,"CitadelCameraSettings_t");inputText=inputText.Replace(node,"");settingsChanged=true;
  }
  var camera=Cameras(b,true);
  var existing=Cameras(a,true);
  bool equal=existing.Length==camera.Length;
  if(equal){try{for(int i=0;i<camera.Length;i++)Equal(existing[i],camera[i]);}catch{equal=false;}}
  if(equal){if(settingsChanged)data["m_modelInfo"]["m_keyValueText"]=new KVObject(inputText);return settingsChanged;}
  var values=KVObject.Array();
  foreach(var v in Cameras(a,false))values.Add(v);
  foreach(var v in camera)values.Add(v);
  var cameraRoot=KVObject.Collection();cameraRoot["AttachmentCameraData"]=values;
  var cameraDocument=new KVDocument(a.Header,a.Name,cameraRoot);
  using var s=new MemoryStream();KVSerializer.Create(KVSerializationFormat.KeyValues3Text).Serialize(s,cameraDocument);
  var serialized=Encoding.UTF8.GetString(s.ToArray());
  var bodyStart=serialized.IndexOf("\n{");if(bodyStart<0)throw new Exception("Camera text serialization format unexpected");
  var snippet=serialized.Substring(bodyStart+2,serialized.LastIndexOf('}')-(bodyStart+2));
  var text=inputText;
  var match=Regex.Match(text,@"\bAttachmentCameraData\s*=\s*\[");
  if(match.Success){
   int depth=1,end=match.Index+match.Length;
   while(depth>0 && end<text.Length){if(text[end]=='[')depth++;if(text[end]==']')depth--;end++;}
   if(depth!=0)throw new Exception("Unbalanced camera metadata");
   text=text.Substring(0,match.Index)+snippet+text.Substring(end);
  }else{text=text.Insert(text.LastIndexOf('}'),snippet);}
  data["m_modelInfo"]["m_keyValueText"]=new KVObject(text);
  return true;
 }
 static void EqualMetadata(string before,string after){
  if(before==after)return;
  var b=Parse(after);var root=ParseRoot(before,after);var a=new KVDocument(b.Header,b.Name,root);
  foreach(var k in a.Root.Keys){if(k!="AttachmentCameraData" && k!="CitadelCameraSettings_t")Equal(a.Root[k],b.Root[k]);}
  foreach(var k in b.Root.Keys){if(k!="AttachmentCameraData" && k!="CitadelCameraSettings_t" && !a.Root.ContainsKey(k))throw new Exception("Added unrelated metadata");}
  var x=Cameras(a,false);var y=Cameras(b,false);if(x.Length!=y.Length)throw new Exception("Changed non-game cameras");
  for(int i=0;i<x.Length;i++)Equal(x[i],y[i]);
 }
 static void Equal(KVObject a, KVObject b, bool pivot=false,string path="") {
  if(path.EndsWith("/m_attachments")){
   var aa=a.Values.Where(v=>!Pivot(v,out _)).ToArray();var bb=b.Values.Where(v=>!Pivot(v,out _)).ToArray();
   if(aa.Length!=bb.Length)throw new Exception("Non-camera attachments changed");
   for(int i=0;i<aa.Length;i++)Equal(aa[i],bb[i]);return;
  }
  if(a.ValueType!=b.ValueType || a.Count!=b.Count)throw new Exception("Changed node type/length");
  if(a.IsCollection){
   if(!a.Keys.SequenceEqual(b.Keys))throw new Exception("Changed keys");
   foreach(var k in a.Keys){
    if(path=="/m_modelInfo" && k=="m_keyValueText"){EqualMetadata(a[k].ToString(),b[k].ToString());continue;}
    if(pivot && (k=="m_vInfluenceOffsets" || k=="m_vInfluenceRotations"))continue;
    bool childPivot=k=="value" && Pivot(a,out _);
    Equal(a[k],b[k],childPivot,path+"/"+k);
   }
  }else if(a.IsArray){for(int i=0;i<a.Count;i++)Equal(a[i],b[i],false,path+"/"+i);}
  else if(a.ToString()!=b.ToString())throw new Exception("Unexpected scalar change at "+path+": "+a.ToString()+" -> "+b.ToString());
 }
 public static void Verify(string before,string after,string original){
  using var a=new Resource();a.Read(before);
  using var b=new Resource();b.Read(after);
  for(int i=0;i<a.Blocks.Count;i++){
   var da=Data(a.Blocks[i]);var db=Data(b.Blocks[i]);
   if(da!=null)Equal(da,db);
  }
  if(Run(after,original,Path.Combine(Path.GetTempPath(),"deadlock-camera-verification"))!="")throw new Exception("Pivot did not match original");
 }
 static bool Pivot(KVObject n, out string name) {
  name="";
  if(!n.IsCollection || !n.ContainsKey("key") || !n.ContainsKey("value")) return false;
  name=n["key"].ToString();
  return AttachmentName(name);
 }
 static void Walk(KVObject n, Action<KVObject,string> visit) {
  if(Pivot(n,out var name)) visit(n["value"],name);
  if(n.IsCollection || n.IsArray) foreach(var c in n.Values) Walk(c,visit);
 }
 static KVObject Data(Block b) => b is KeyValuesOrNTRO k ? k.Data : b is BinaryKV3 v ? v.Data.Root : null;
 static string Vec(KVObject n) => string.Join(",",n.Values.Select(x=>x.ToString()));
 static double Number(KVObject n)=>double.Parse(n.ToString(),CultureInfo.InvariantCulture);
 static void RootCompatible(KVObject mod,KVObject original,Dictionary<string,KVObject> targets){
  var a=mod["m_modelSkeleton"];var b=original["m_modelSkeleton"];
  foreach(var bone in targets.Values.SelectMany(v=>v["m_influenceNames"].Values).Select(v=>v.ToString()).Where(s=>s.Length>0).Distinct()){
   int ia=a["m_boneName"].Values.Select(v=>v.ToString()).ToList().IndexOf(bone);
   int ib=b["m_boneName"].Values.Select(v=>v.ToString()).ToList().IndexOf(bone);
   if(ia<0 || ib<0)throw new Exception("Camera influence bone missing: "+bone);
   if(Number(a["m_nParent"][ia])!=-1 || Number(b["m_nParent"][ib])!=-1)throw new Exception("Non-root camera influence requires manual rig conversion: "+bone);
   for(int i=0;i<3;i++)if(Math.Abs(Number(a["m_bonePosParent"][ia][i])-Number(b["m_bonePosParent"][ib][i]))>0.05)throw new Exception("Camera root position differs from native rig");
   double dot=0;for(int i=0;i<4;i++)dot+=Number(a["m_boneRotParent"][ia][i])*Number(b["m_boneRotParent"][ib][i]);
   if(Math.Abs(dot)<0.9999)throw new Exception("Camera root rotation differs from native rig");
   if(a.ContainsKey("m_boneScaleParent") && b.ContainsKey("m_boneScaleParent") && Math.Abs(Number(a["m_boneScaleParent"][ia])-Number(b["m_boneScaleParent"][ib]))>0.001)throw new Exception("Camera root scale differs from native rig");
  }
 }
 public static string Run(string mod, string original, string output) {
  using var r=new Resource(); r.Read(mod);
  using var o=new Resource(); o.Read(original);
  var pivots=new Dictionary<string,KVObject>();
  foreach(var b in o.Blocks) { var d=Data(b); if(d!=null) Walk(d,(v,n)=>{if(!pivots.ContainsKey(n))pivots[n]=v;}); }
  var log=new List<string>();
  var originalModel=Data(o.Blocks.First(b=>b.Type.ToString()=="DATA"));
  if(pivots.Count==0)return "";
  RootCompatible(Data(r.Blocks.First(b=>b.Type.ToString()=="DATA")),originalModel,pivots);
  bool anyExisting=false;
  foreach(var block in r.Blocks){var d=Data(block);if(d!=null)Walk(d,(v,n)=>{anyExisting=true;});}
  bool addedFirst=false;
  if(!r.Blocks.Any(b=>b.Type.ToString()=="MDAT"))throw new Exception("External mesh camera data is not supported by this tool");
  foreach(var b in r.Blocks) {
   var d=Data(b); if(d==null)continue;
   int edits=0;
   if(b.Type.ToString()=="DATA" && Metadata(d,originalModel)){edits++;log.Add("DATA camera FOV metadata synchronized");}
   if(b.Type.ToString()=="MDAT" && d.ContainsKey("m_attachments")){
    var existing=d["m_attachments"].Values.Where(v=>Pivot(v,out _)).ToArray();
    if(existing.Length>0 || (!anyExisting && !addedFirst)){
     bool same=existing.Length==pivots.Count;
     if(same){try{foreach(var v in existing){var n=v["key"].ToString();if(!pivots.ContainsKey(n)){same=false;break;}Equal(v["value"],pivots[n]);}}catch{same=false;}}
     if(!same){
      var array=KVObject.Array();foreach(var v in d["m_attachments"].Values)if(!Pivot(v,out _))array.Add(v);
      foreach(var pair in pivots){var v=KVObject.Collection();v["key"]=new KVObject(pair.Key);v["value"]=pair.Value;array.Add(v);}
      d["m_attachments"]=array;edits++;log.Add("MDAT "+r.Blocks.ToList().IndexOf(b)+": synchronized "+pivots.Count+" native camera attachments");
     }
     addedFirst=true;
    }
   }
   if(edits>0){Directory.CreateDirectory(output);using var s=File.Create(Path.Combine(output,b.Type+"-"+r.Blocks.ToList().IndexOf(b)+".bin"));b.Serialize(s);}
  }
  if(!addedFirst)throw new Exception("No supported embedded mesh attachment container");
  return string.Join("\n",log);
 }
}




