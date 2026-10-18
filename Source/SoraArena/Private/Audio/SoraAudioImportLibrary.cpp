#include "Audio/SoraAudioImportLibrary.h"

#include "Sound/SoundClass.h"
#include "Sound/SoundSubmix.h"

#if WITH_EDITOR
bool USoraAudioImportLibrary::SetSubmixParent(USoundSubmix* Child, USoundSubmix* Parent)
{
    if (!Child || !Parent)
        return false;
    // Parent may not be Child or descend from it.
    for (const USoundSubmixBase* Ancestor = Parent; Ancestor;)
    {
        if (Ancestor == Child)
            return false;
        const USoundSubmixWithParentBase* Linked = Cast<USoundSubmixWithParentBase>(Ancestor);
        Ancestor = Linked ? Linked->ParentSubmix.Get() : nullptr;
    }
    Child->SetParentSubmix(Parent);
    return true;
}

bool USoraAudioImportLibrary::SetSoundClassParent(USoundClass* Child, USoundClass* Parent)
{
    if (!Child || !Parent || Child == Parent || Child->RecurseCheckChild(Parent))
        return false;
    // SetParentClass leaves the new parent's child list to the caller.
    Child->SetParentClass(Parent);
    Parent->Modify();
    Parent->ChildClasses.AddUnique(Child);
    return true;
}
#endif
