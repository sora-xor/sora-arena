#include "SoraHelmRules.h"
#include <cassert>
#include <iostream>
using namespace SoraHelmRules;
struct Fixture {
 FContract C; FState S; SoraBeatRules::FTask T; SoraBeatRules::FTaskState B;
 Fixture() { T.Type=SoraBeatRules::EType::ProductionTask; T.Task=SoraBeatRules::ETask::Hold; T.Goal=SoraBeatRules::EGoal::Hold; T.DurationMs=60000; T.Contest=SoraBeatRules::EContest::Pause; S.DeadlineMs=C.DeadlineMs[1]; }
 void tick(int ms,bool at=true,bool contest=false,bool held=false) { SoraBeatRules::FTick step;step.DeltaMs=ms;step.AtTask=at;step.Contested=contest;Tick(S,C,B,T,step,held); }
};
int main() {
 assert(Valid(FContract{}));
 for(int frame: {1,7,16,17,33,250,1000,60000}) {
  Fixture f;
  for(int elapsed=0;elapsed<25000;) { int d=frame<25000-elapsed?frame:25000-elapsed;f.tick(d);elapsed+=d; }
  assert(f.S.Raised==1&&f.S.Pending==0&&f.S.GraceMs==0);
  assert(f.B.ElapsedMs==25000&&f.B.Progress==20600); // 23s earned minus 2s × 1.2s/s.
  f.S.Working=true;f.tick(1999,true,false,true);assert(f.S.Pending==0&&f.S.HeldMs==1999);
  f.tick(1,true,false,true);assert(f.S.Pending==-1&&f.S.Corrected==1&&f.B.Progress==18203);
 }
 Fixture ignored;ignored.tick(60000);assert(ignored.B.Progress==0&&!ignored.S.Failed);
 ignored.tick(60000,false);ignored.tick(30000,false);assert(ignored.S.Failed&&ignored.B.ElapsedMs==150000);
 Fixture grace;grace.tick(15000);assert(grace.S.GraceMs==8000&&grace.B.Progress==15000);
 grace.tick(8000);assert(grace.B.Progress==23000&&grace.S.GraceMs==0);
 grace.tick(1000);assert(grace.B.Progress==21800);
 Fixture cancelled;cancelled.tick(15000);cancelled.S.Working=true;cancelled.tick(1000,true,false,true);
 cancelled.tick(1,true,false,false);assert(!cancelled.S.Working&&cancelled.S.HeldMs==0&&cancelled.S.Pending==0);
 Fixture all;
 while(!SoraBeatRules::TaskComplete(all.B,all.T)&&!all.S.Failed) {
  if(all.S.Pending>=0) all.S.Working=true;
  all.tick(17,true,false,all.S.Pending>=0);
 }
 assert(all.S.Raised==7&&all.S.Corrected==7&&!all.S.Failed&&all.B.Progress==60000&&all.B.ElapsedMs==60000);
 all.tick(60000);assert(all.B.ElapsedMs==60000);
 for(int difficulty=0;difficulty<3;++difficulty) {
  Fixture f;f.S.DeadlineMs=f.C.DeadlineMs[difficulty];
  while(f.B.ElapsedMs<f.S.DeadlineMs-1) f.tick((f.S.DeadlineMs-f.B.ElapsedMs-1)>60000?60000:f.S.DeadlineMs-f.B.ElapsedMs-1,false);
  assert(!f.S.Failed&&f.B.Progress==0);f.tick(1,false);assert(f.S.Failed);
 }
 Fixture contested;contested.tick(15000,true,true);assert(contested.B.Progress==0&&contested.B.ElapsedMs==15000);
 for(int i=0;i<3;++i) { auto c=FContract{};c.Threshold[i]=0;assert(!Valid(c)); }
 auto bad=FContract{};bad.WorkMs=8001;assert(!Valid(bad));
 std::cout<<"Helm rules: frame partition, three corrections, grace/decay, interruption, contest and difficulty deadline passed\n";
}
