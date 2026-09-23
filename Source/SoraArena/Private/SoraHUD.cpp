#include "SoraHUD.h"
#include "SoraCharacter.h"
#include "SoraGameMode.h"
#include "SoraCatalog.h"
#include "SoraWorldBuilder.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/Font.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Fonts/CompositeFont.h"
#include "ArenaWalletSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "ArenaKernelSubsystem.h"
#include "Engine/Texture2D.h"

void ASoraHUD::Label(const FString& T,float X,float Y,float S,FLinearColor C)
{
    if(!JapaneseFont)
    {
        JapaneseFont=NewObject<UFont>(this);
        JapaneseFont->FontCacheType=EFontCacheType::Runtime;
        JapaneseFont->LegacyFontSize=28;
        JapaneseFont->LegacyFontName=FName(TEXT("Regular"));
        JapaneseFont->CompositeFont=FCompositeFont(FName(TEXT("Regular")),FPaths::ProjectContentDir()/TEXT("SourceArt/Fonts/NotoSansCJKjp-Regular.otf"),EFontHinting::Default,EFontLoadingPolicy::LazyLoad);
    }
    DrawText(T,C,X,Y,JapaneseFont,S,false);
}
int32 ASoraHUD::WrappedLabel(const FString& Text,float X,float Y,float Scale,FLinearColor Color,float MaxWidth,float LineHeight,int32 MaxLines)
{
    FString Line; int32 Count=0;
    for(int32 I=0;I<Text.Len();++I)
    {
        const FString Candidate=Line+Text.Mid(I,1); float Width=0,Height=0;
        GetTextSize(Candidate,Width,Height,JapaneseFont,Scale);
        if((Width>MaxWidth&&!Line.IsEmpty())||Text[I]=='\n')
        {
            Label(Line,X,Y+Count*LineHeight,Scale,Color); ++Count; Line.Empty();
            if(Count>=MaxLines) return Count;
        }
        if(Text[I]!='\n') Line+=Text.Mid(I,1);
    }
    if(!Line.IsEmpty()&&Count<MaxLines) { Label(Line,X,Y+Count*LineHeight,Scale,Color); ++Count; }
    return Count;
}
void ASoraHUD::Panel(float X,float Y,float W,float H,FLinearColor C) { DrawRect(C,X,Y,W,H); }
void ASoraHUD::DrawHUD()
{
    Super::DrawHUD(); if(!Canvas) return;
    auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    auto* P=Cast<ASoraCharacter>(UGameplayStatics::GetPlayerPawn(this,0)); if(!G) return;
    const float W=Canvas->SizeX,H=Canvas->SizeY;
    const float S=FMath::Clamp(FMath::Min(W/1600.f,H/1000.f),.45f,1.5f);
    const FLinearColor Ivory(.93,.90,.80),Gold(.94,.65,.21),Teal(.22,.81,.75),Muted(.56,.63,.65);
    if(!FSoraCatalog::Get().IsReady()) { Label(TEXT("SORA ARENA / コンテンツの読み込みエラー"),50,60,1,Gold); Label(FSoraCatalog::Get().Error,50,110,.65,Ivory); return; }
    Panel(0,0,W,75*S,FLinearColor(.018,.035,.045,.86));
    if(!bResistanceLogoResolved)
    {
        ResistanceLogo=LoadObject<UTexture2D>(nullptr,TEXT("/Game/Generated/UI/T_SoraResistanceLogo.T_SoraResistanceLogo"),nullptr,LOAD_NoWarn);
        bResistanceLogoResolved=true;
    }
    if(ResistanceLogo) DrawTexture(ResistanceLogo,28*S,13*S,48*S,48*S,0,0,1,1,FLinearColor::White);
    Label(TEXT("SORA 抵抗軍  /  猫柳生"),ResistanceLogo?90*S:30*S,18*S,.9*S,Ivory);
    Label(TEXT("オフライン開発版  |  XOR・NFT の送金は行いません"),W-650*S,24*S,.47*S,Teal);
    if(G->bMenu)
    {
        if(!bTitleArtResolved)
        {
            TitleArt=LoadObject<UTexture2D>(nullptr,TEXT("/Game/Generated/UI/T_NyaagyuTitle.T_NyaagyuTitle"),nullptr,LOAD_NoWarn); bTitleArtResolved=true;
        }
        if(TitleArt)
        {
            const float AreaH=H-75*S,ImageAspect=static_cast<float>(TitleArt->GetSizeX())/FMath::Max(1,TitleArt->GetSizeY());
            const float Aspect=W/FMath::Max(1.f,AreaH);
            const float USize=FMath::Min(1.f,Aspect/ImageAspect),VSize=FMath::Min(1.f,ImageAspect/Aspect);
            DrawTexture(TitleArt,0,75*S,W,AreaH,(1-USize)*.5f,(1-VSize)*.5f,USize,VSize,FLinearColor(1,1,1,.8f));
        }
        Panel(0,75*S,W,H,FLinearColor(.013,.027,.033,TitleArt?.58f:.9f));
        Panel(40*S,95*S,1190*S,700*S,FLinearColor(.013,.027,.033,.45f));
        const float L=80*S;
        Label(TEXT("剣を、工房を、民の手に。"),L,112*S,.55*S,Gold);
        Label(TEXT("猫柳生"),L,155*S,2.8*S,Ivory);
        Label(TEXT("ニャーギュウ ― 異星の債務帝国に挑む、侍猫の物語。"),L,245*S,.65*S,Muted);
        FString MenuChapter = TEXT("稽古場");
        if(G->bDeterministicPractice) MenuChapter=TEXT("武芸稽古 / オフライン");
        else if(G->bCampaignComplete&&G->bCampaign) MenuChapter=TEXT("猫柳生、解放済み");
        else if(G->bCampaign) MenuChapter=FString::Printf(TEXT("第 %02d 章  /  %s"),G->ChapterId+1,*FSoraCatalog::Get().Chapter(G->ChapterId).Title);
        Label(MenuChapter,L,300*S,.8*S,Teal);
        Label(FString::Printf(TEXT("%s  |  %s"),*FSoraCatalog::Get().Map(G->MapId).Name,*FSoraCatalog::Get().Class(G->SelectedClass).Role),L,340*S,.6*S,Ivory);
        Label(G->bCampaignComplete&&G->bCampaign?TEXT("物語は完結した。N はじめから   P 武芸稽古   M マップ変更"):TEXT("ENTER 続ける   B 保存した物語へ   N はじめから   P 武芸稽古   M マップ変更"),L,397*S,.52*S,Ivory);
        Label(TEXT("流儀を選ぶ  /  変更すると、この戦いをやり直します"),L,465*S,.55*S,Gold);
        for(int32 I=0;I<6;++I)
        {
            const float X=L+(I%3)*385*S,Y=(515+(I/3)*84)*S;
            Panel(X-10*S,Y-8*S,355*S,69*S,I==G->SelectedClass?FLinearColor(.08,.25,.26,.9):FLinearColor(.07,.095,.11,.9));
            Label(FString::Printf(TEXT("F%d   %s"),I+1,*FSoraCatalog::Get().Class(I).Name),X,Y,.68*S,I==G->SelectedClass?Teal:Ivory);
            Label(FSoraCatalog::Get().Class(I).Role,X,Y+28*S,.42*S,Muted);
        }
        if(G->bDeterministicPractice)
        {
            const int32 Weapon=FSoraCatalog::Get().Class(G->SelectedClass).Weapons[G->PracticeWeaponSlot];
            Label(TEXT("入場時の武器： ")+FSoraCatalog::Get().Weapon(Weapon).Name+TEXT("  /  メニューで 1 主武器・2 近接・3 特殊を選択"),L,680*S,.46*S,Gold);
            Label(TEXT("WASD 移動   マウス 照準   左クリック 射撃   右クリック 近接   R 装填   Ctrl 防御   Q 技   Space 跳躍"),L,725*S,.50*S,Ivory);
            Label(TEXT("武器は稽古中に変更できません。Esc メニュー / F10 英語字幕。XOR 入金・オンライン対戦はありません。"),L,763*S,.45*S,Ivory);
            if(auto* K=G->Kernel()) if(!K->PracticeError.IsEmpty()) WrappedLabel(K->PracticeError,L,435*S,.4*S,Gold,W-L*2,20*S,1);
        }
        else
        {
            Label(TEXT("WASD 移動   マウス 照準   左クリック 射撃   右クリック 斬撃   Shift 疾走   Space 跳躍"),L,725*S,.55*S,Ivory);
            Label(TEXT("1 主武器   2 近接武器   3 特殊武器の試用   R 装填   E 調べる   Esc メニュー   F10 英語字幕"),L,763*S,.55*S,Ivory);
        }
        Label(TEXT("IROHA CONNECT  /  C 接続を開始   L ウォレットを開く   X 接続を解除"),L,815*S,.52*S,Gold);
        if(auto* Wallet=GetWorld()->GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>())
        {
            WrappedLabel(Wallet->StatusText,L,852*S,.46*S,Muted,W-L*2,23*S,2);
            if(!Wallet->ApprovedAccount.IsEmpty()) Label(TEXT("承認済み： ")+Wallet->ApprovedAccount.Left(62),L,902*S,.42*S,Teal);
            if(Wallet->State==EArenaWalletState::AwaitingApproval&&Wallet->WalletQrTexture)
            {
                const int32 Pixels=Wallet->WalletQrTexture->GetSizeX();
                const int32 IntegerScale=FMath::Min(3,FMath::FloorToInt((W-1260*S)/FMath::Max(Pixels,1)));
                if(IntegerScale>=1)
                {
                    const float Size=Pixels*IntegerScale;
                    const float QX=FMath::FloorToFloat(W-Size-25*S),QY=FMath::FloorToFloat(210*S);
                    DrawTextureSimple(Wallet->WalletQrTexture,QX,QY,static_cast<float>(IntegerScale),false);
                    Label(TEXT("接続用 QR / この画面のみ"),QX,QY+Size+12*S,.36*S,Muted);
                }
                else Label(TEXT("QR 表示には画面を広げてください"),L,902*S,.42*S,Muted);
            }
        }
        Label(TEXT("ウォレット接続は資産の預入ではありません。対戦決済・NFT 売買は未公開です。"),L,940*S,.42*S,Muted);
        Label(TEXT("日本語・英語字幕付き。全八章の試作戦闘 / 音声未収録。環境素材：Powered by Poly Haven (CC0)"),L,970*S,.38*S,Muted);
        if(TitleArt) Label(TEXT("背景：生成キービジュアル / ゲーム画面ではありません"),W-600*S,100*S,.35*S,Muted);
        if(auto* Kernel=GetWorld()->GetGameInstance()->GetSubsystem<UArenaKernelSubsystem>()) Label(Kernel->StatusText,W-690*S,53*S,.34*S,Muted);
        return;
    }
    Label(G->bCampaign?FSoraCatalog::Get().Chapter(G->ChapterId).Title:FSoraCatalog::Get().Map(G->MapId).Name,30*S,95*S,.82*S,Ivory);
    Label(G->ObjectiveText(),30*S,137*S,.52*S,Teal);
    if(P)
    {
        if(P->DamageFlash>0) { Panel(0,0,12*S,H,FLinearColor(.8,0,0,.65)); Panel(W-12*S,0,12*S,H,FLinearColor(.8,0,0,.65)); }
        const float CX=W*.5f,CY=H*.5f; const FLinearColor Cross=P->HitMarkerTime>0?Gold:Ivory;
        DrawLine(CX-10,CY,CX-4,CY,Cross,1.5); DrawLine(CX+4,CY,CX+10,CY,Cross,1.5); DrawLine(CX,CY-10,CX,CY-4,Cross,1.5); DrawLine(CX,CY+4,CX,CY+10,Cross,1.5);
        Panel(25*S,H-110*S,340*S,80*S,FLinearColor(.015,.035,.05,.9));
        Label(FString::Printf(TEXT("%03d"),FMath::CeilToInt(P->Health)),45*S,H-103*S,1.5*S,Ivory);
        Label(FSoraCatalog::Get().Class(P->ClassId).Name,140*S,H-82*S,.65*S,Teal);
        Panel(45*S,H-45*S,290*S,4*S,FLinearColor(.12,.19,.21)); Panel(45*S,H-45*S,290*S*FMath::Clamp(P->Health/P->MaxHealth,0.f,1.f),4*S,Teal);
        const auto& Weapon=FSoraCatalog::Get().Weapon(P->WeaponId);
        Panel(W-390*S,H-110*S,365*S,80*S,FLinearColor(.015,.035,.05,.9));
        Label(Weapon.Name,W-365*S,H-96*S,.72*S,Ivory);
        if(G->bDeterministicPractice)
        {
            if(auto* K=G->Kernel()) if(K->PracticePlayers.Num()>0)
            {
                const auto& State=K->PracticePlayers[0];
                const FString Ammunition=State.Magazine==0?TEXT("剣術 / 右クリック"):
                    State.ReloadTicks>0?FString::Printf(TEXT("装填中 %.1f 秒   %d / %d"),State.ReloadTicks/60.f,State.Ammo,State.Magazine):
                    FString::Printf(TEXT("弾数 %02d / %02d   R 装填"),State.Ammo,State.Magazine);
                Label(Ammunition,W-365*S,H-71*S,.46*S,Gold);
                Label(FString::Printf(TEXT("気力 %d / 100    待機 %.2f 秒"),State.Stamina,State.Cooldown/60.f),W-365*S,H-48*S,.33*S,Muted);
                if(!State.Alive)
                {
                    Panel(W*.25,H*.35,W*.5,120*S,FLinearColor(.013,.027,.033,.88f));
                    Label(FString::Printf(TEXT("%.1f 秒後に復帰します"),State.RespawnTicks/60.f),W*.3,H*.38,.9*S,Gold);
                    if(G->bEnglishSubtitles) Label(TEXT("Respawning — no stake is at risk."),W*.3,H*.38+48*S,.45*S,Ivory);
                }
                if(G->bPracticeSlowed) Label(TEXT("処理負荷により、稽古時間を減速しています"),30*S,200*S,.4*S,Gold);
            }
        }
        else Label(P->bReloading?TEXT("装填中"):Weapon.Kind==TEXT("melee")?TEXT("剣術 / 右クリック"):FString::Printf(TEXT("%02d / %02d   R 装填"),P->Ammo,Weapon.Magazine),W-365*S,H-59*S,.54*S,Gold);
        if(G->Arena()&&!G->bDeterministicPractice)
        {
            for(int32 I=0;I<G->Arena()->NodePositions.Num();++I)
            {
                const FVector Position=G->Arena()->NodePositions[I]+FVector(0,0,250);
                if(FVector::DotProduct(Position-P->GetActorLocation(),P->GetActorForwardVector())>0)
                {
                    const FVector Screen=Project(Position); const int32 M=FMath::RoundToInt(FVector::Dist2D(Position,P->GetActorLocation())/100);
                    if(Screen.X>0&&Screen.X<W&&Screen.Y>170*S&&Screen.Y<H-120*S) Label(FString::Printf(TEXT("工房 %d / %dm"),I+1,M),Screen.X-75*S,Screen.Y,.42*S,Teal);
                }
            }
            bool Near=false; for(auto Pos:G->Arena()->NodePositions) Near|=FVector::Dist2D(Pos,P->GetActorLocation())<230;
            Near|=FVector::Dist2D(G->Arena()->ExitPoint(),P->GetActorLocation())<270;
            if(Near) Label(TEXT("E  調べる"),CX-75*S,CY+60*S,.65*S,Gold);
        }
    }
    if(const auto* Cue=G->CurrentDialogueCue())
    {
        // Timed story cues are overlays; gameplay input and objective timers continue.
        Panel(20*S,H-400*S,W-40*S,125*S,FLinearColor(.013,.027,.033,.93));
        if(const auto* Speaker=FSoraCatalog::Get().DialogueSpeaker(Cue->SpeakerId))
        {
            Label(Speaker->Japanese,35*S,H-392*S,.46*S,Gold);
            if(G->bEnglishSubtitles) Label(Speaker->English,W-285*S,H-392*S,.38*S,Muted);
        }
        WrappedLabel(Cue->Japanese,35*S,H-358*S,.57*S,Ivory,W-70*S,24*S,2);
        if(G->bEnglishSubtitles) WrappedLabel(Cue->English,35*S,H-312*S,.43*S,Muted,W-70*S,20*S,2);
    }
    if(G->NoticeTime>0)
    {
        Panel(20*S,H-255*S,W-40*S,110*S,FLinearColor(.015,.035,.045,.94));
        WrappedLabel(G->Notice,35*S,H-245*S,.55*S,Ivory,W-70*S,24*S,2);
        if(G->bEnglishSubtitles) WrappedLabel(G->NoticeEnglish,35*S,H-190*S,.43*S,Muted,W-70*S,20*S,2);
    }
    if(G->bDefeated||G->bChapterComplete)
    {
        Panel(0,H*.3,W,H*.35,FLinearColor(.012,.026,.034,.94));
        Label(G->bDeterministicPractice?TEXT("稽古終了"):G->bDefeated?TEXT("ふたたび立ち上がれ"):G->bCampaignComplete?TEXT("猫柳生、解放"):TEXT("街区を解放した"),W*.2,H*.36,1.8*S,G->bDefeated?Gold:Teal);
        WrappedLabel(G->Notice,W*.2,H*.48,.65*S,Ivory,W*.65,29*S,2);
        if(G->bEnglishSubtitles) WrappedLabel(G->NoticeEnglish,W*.2,H*.535,.42*S,Muted,W*.65,20*S,2);
        Label(TEXT("ENTER  続ける    |    ESC  メニュー"),W*.2,H*.56,.65*S,Muted);
    }
}
