# التثبيت

**لا** تحتاج إلى Python أو أي شيء آخر لاستخدام PrintView3D. اختر نظامك:

| النظام | التنزيل | |
|---|---|---|
| **Windows 10 / 11** | `PrintView3D-Setup.exe` (أو النسخة المحمولة `PrintView3D-windows.zip`) | [التعليمات](#windows) |
| **Linux** (‏64 بت، x86-64) | `PrintView3D-x86_64.AppImage` | [التعليمات](#linux) |
| **macOS 14.4+** (‏Apple silicon: ‏M1 وأحدث)، تجريبي | `PrintView3D-macOS-AppleSilicon.dmg` | [التعليمات](#macos) |
| **macOS 14.4+** (‏Intel)، تجريبي | `PrintView3D-macOS-Intel.dmg` | [التعليمات](#macos) |

كل التنزيلات موجودة في صفحة **[أحدث إصدار](https://github.com/sevagjb/PrintView3D/releases/latest)**.

## Windows {#windows}

1. اذهب إلى **[أحدث إصدار](https://github.com/sevagjb/PrintView3D/releases/latest)** ونزّل **`PrintView3D-Setup.exe`**.
2. انقر عليه نقرًا مزدوجًا ثم **Next ← Install ← Finish**.
    - يُثبَّت لحساب المستخدم الخاص بك فقط، لذلك **لا حاجة إلى كلمة مرور المسؤول**.
    - يضيف PrintView3D إلى قائمة ابدأ (واختصارًا على سطح المكتب إن أردت) وإلى «فتح باستخدام» لملفات
      `.stl` و`.3mf` و`.gcode`.
3. يبدأ PrintView3D. انتهى.

**المعاينات في مستكشف الملفات:** يعرض المثبّت أيضًا **صورًا مصغّرة لملفات 3MF وSTL وG-code وFreeCAD**
في مستكشف الملفات (يمكنك إلغاء تحديد ذلك أثناء التثبيت). تعرض ملفات 3MF وG-code وFreeCAD صورة المعاينة
التي حفظها برنامج التقطيع أو FreeCAD؛ أما ملفات STL فتُرسَم. إذا لم تظهر الصور المصغّرة فورًا، فبدّل عرض
المجلد إلى *أيقونات كبيرة*، أو سجّل الخروج ثم الدخول مجددًا. (إذا كانت إضافات مستكشف الملفات في PowerToys
مفعّلة، فسيستمر PowerToys في عرض صور STL وG-code المصغّرة.)

**التحديث:** نزّل ملف `PrintView3D-Setup.exe` الجديد وشغّله. يحلّ محل الإصدار القديم ويحتفظ بإعداداتك.

> **ظهرت رسالة «Windows protected your PC»؟** الإصدارات غير موقّعة رقميًا بعد (تم التقدّم بطلب توقيع
> مجاني عبر SignPath Foundation، راجع [سياسة توقيع الشيفرة](contribute.md#code-signing-policy))، لذلك
> قد يحذّرك Windows SmartScreen في المرة الأولى. انقر **More info ← Run anyway**. كل الشيفرة المصدرية
> موجودة في المستودع، وكل إصدار يُبنى تلقائيًا بواسطة [GitHub Actions](https://github.com/sevagjb/PrintView3D/actions)
> من تلك الشيفرة.

**النسخة المحمولة:** نزّل `PrintView3D-windows.zip` واستخرجه وشغّل `PrintView3D.exe`. لا يُثبَّت أي شيء.
(لا يزال `install_windows.bat` الموجود في الملف المضغوط يعمل أيضًا.)

### اجعله البرنامج الافتراضي للملفات ثلاثية الأبعاد (اختياري)

1. في PrintView3D، انقر **الإعدادات**.
2. افتح صفحة **الملفات** وانقر **تسجيل واختياره كافتراضي…**.
3. تُفتح إعدادات Windows. اختر **PrintView3D** لملفات `.stl` و`.3mf` و`.gcode`.

يشترط Windows أن تؤكد هذه الخطوة الأخيرة بنفسك؛ لا يُسمح لأي برنامج بفعلها دون علمك.
زر **إزالة التسجيل** في المكان نفسه يتراجع عن كل شيء.

### إلغاء التثبيت

**إعدادات Windows ← التطبيقات ← التطبيقات المثبتة ← PrintView3D ← إلغاء التثبيت**. يزيل ذلك البرنامج
واختصاراته وارتباطات الملفات، ويسألك هل تريد حذف إعداداتك أيضًا.
(النسخة المحمولة: شغّل `uninstall_windows.bat` من المجلد المستخرج.)

## Linux {#linux}

نسخة Linux من PrintView3D ملف **AppImage** واحد: يحتوي كل ما يحتاجه ويعمل على معظم التوزيعات دون تثبيت
حزم: Ubuntu 22.04 أو أحدث، وLinux Mint 21+، وDebian 12+، وFedora 36+، وopenSUSE Tumbleweed، وArch،
وManjaro، وPop!_OS، وelementary OS، وZorin OS وغيرها.

1. نزّل **`PrintView3D-x86_64.AppImage`** من **[أحدث إصدار](https://github.com/sevagjb/PrintView3D/releases/latest)**.
2. اجعله قابلًا للتشغيل: انقر عليه بالزر الأيمن ← **Properties ← Permissions ← Allow executing file as
   program**، أو في الطرفية:
   ```bash
   chmod +x PrintView3D-x86_64.AppImage
   ```
3. انقر عليه نقرًا مزدوجًا، أو شغّل `./PrintView3D-x86_64.AppImage`.

**أضفه إلى قائمة التطبيقات** (اختياري، يُنصح به): في PrintView3D افتح **الإعدادات ← الملفات** وانقر
**تسجيل وجعله افتراضيًا**. يظهر PrintView3D بعدها في قائمة التطبيقات وفي «فتح باستخدام»، ويفتح ملفات
`.stl` و`.3mf` و`.gcode` بالنقر المزدوج. على Linux يسري ذلك فورًا؛ وزر **إزالة التسجيل** يتراجع عنه.

نصيحة: ضع ملف AppImage في مكان ثابت مثل `~/Applications` قبل التسجيل، لأن مدخل القائمة يشير إلى مكان
الملف. أو دع السكربت يقوم بكل شيء:

```bash
./install_linux.sh PrintView3D-x86_64.AppImage     # copies to ~/Applications + adds the menu entry
./uninstall_linux.sh                               # removes it again
```

(السكربتان موجودان في [الشيفرة المصدرية](https://github.com/sevagjb/PrintView3D/archive/refs/heads/main.zip).)

**برامج التقطيع على Linux** يُعثَر عليها تلقائيًا عند تثبيتها كـ AppImage (في `~/Applications` و
`~/Downloads` و`~/Desktop` و`~/bin` و`/opt`…)، أو كـ **Flatpak** أو **Snap**، أو من حزم توزيعتك، أو في
`/opt`. وإلا فاخترها مرة واحدة بزر **استعراض…** في الإعدادات.

<details markdown>
<summary><b>حل مشكلات Linux</b></summary>

| المشكلة | الحل |
|---|---|
| لا يحدث شيء / ‏«AppImages require FUSE» | ثبّت FUSE: ‏`sudo apt install libfuse2` (Ubuntu/Debian)، ‏`sudo dnf install fuse fuse-libs` (Fedora). أو شغّله دون FUSE: ‏`./PrintView3D-x86_64.AppImage --appimage-extract-and-run` |
| `GLIBC_2.35 not found` | توزيعتك أقدم من Ubuntu 22.04 / Debian 12. ابنِ البرنامج من الشيفرة المصدرية بدلًا من ذلك ([البناء بنفسك](build.md)). |
| تُفتح النافذة لكن العرض ثلاثي الأبعاد يبقى أسود | تأكد من تثبيت تعريف بطاقة الرسوميات (Mesa أو تعريف NVIDIA). في الجهاز الافتراضي، فعّل تسريع 3D. |
| سطح مكتب Wayland | مدعوم. يعمل PrintView3D تلقائيًا عبر XWayland، لأن العرض ثلاثي الأبعاد يحتاجه. |
| تدوير بطيء على حاسوب محمول ببطاقتي رسوميات | شغّل PrintView3D من قائمة التطبيقات بعد **التسجيل** (مدخل القائمة يطلب البطاقة المخصصة)، أو استخدم خيار *Launch using Dedicated Graphics Card* في سطح المكتب. |

</details>

## macOS {#macos}

> **تجريبي.** تُبنى نسخة Mac وتُفحَص تلقائيًا، لكن لم يجرّبها كثيرون على أجهزة Mac حقيقية بعد. رجاءً
> [أخبرنا كيف تعمل](https://github.com/sevagjb/PrintView3D/issues/new?template=mac_build.md): طراز جهاز
> Mac، وإصدار macOS، وأي شيء يبدو خاطئًا.

لنظام **macOS 14.4 ‏(Sonoma) أو أحدث**، بنسختين؛ اختر النسخة المناسبة لجهازك
(قائمة Apple ← **About This Mac**: ‏*Chip* تعني Apple silicon، و*Processor* تعني Intel):

| جهاز Mac لديك | التنزيل |
|---|---|
| **Apple silicon** ‏(M1 وM2 وM3 وM4 وأحدث) | `PrintView3D-macOS-AppleSilicon.dmg` |
| **Intel** ‏(من 2018 وأحدث، أي الأجهزة التي تعمل بنظام macOS 14) | `PrintView3D-macOS-Intel.dmg` |

1. من **[أحدث إصدار](https://github.com/sevagjb/PrintView3D/releases/latest)** نزّل ملف `.dmg` المناسب لجهازك.
2. افتحه واسحب **PrintView3D** إلى **Applications**.
3. شغّل PrintView3D من Applications. **في المرة الأولى** يقول macOS إنه *لا يستطيع التحقق* من التطبيق.
   انقر **Done** (وليس «Move to Trash»).
4. افتح **System Settings ← Privacy & Security**، ومرّر إلى *Security* وانقر **Open Anyway** بجانب
   PrintView3D. أكّد بكلمة المرور أو Touch ID.

بعد ذلك يُفتح بشكل طبيعي.

> **لماذا هذه الخطوة الإضافية؟** لا تتخطاها Apple إلا للتطبيقات من مطوّرين يدفعون لها سنويًا مقابل شهادة
> و«توثيق» (notarization). ‏PrintView3D مجاني ولا ميزانية له لذلك، فهو موقّع دون حساب Apple. البرنامج هو
> الشيفرة المفتوحة المصدر نفسها كما في Windows وLinux، ويُبنى تلقائيًا بواسطة
> [GitHub Actions](https://github.com/sevagjb/PrintView3D/actions). (لم يعد النقر بالزر الأيمن ← Open يعمل
> لهذا الغرض في macOS 15 وأحدث؛ استخدم Open Anyway كما في الأعلى.)

**افتح الملفات باستخدام PrintView3D:** في Finder، انقر بالزر الأيمن على ملف `.stl` أو `.3mf` أو `.gcode`
أو `.FCStd` ← **Open With ← PrintView3D**. لجعله افتراضيًا: انقر بالزر الأيمن على الملف ← **Get Info** ←
*Open with:* ‏**PrintView3D** ← **Change All…**.

**برامج التقطيع** في Applications ‏(Creality Print وOrcaSlicer وBambu Studio وPrusaSlicer وCura و…)
يُعثَر عليها تلقائيًا. **التحديثات:** يفتح زر *تنزيل التحديث* صفحة الإصدار؛ اسحب الإصدار الجديد إلى
Applications ليحلّ محل القديم. أجهزة Mac الأقدم التي لا تعمل بنظام macOS 14:
[أخبرنا](https://github.com/sevagjb/PrintView3D/issues/new?template=mac_build.md) إن كنت تحتاج إلى نسخة لها.


### ‏Quick Look (معاينات Finder) {#quick-look}

يضيف PrintView3D دعم Quick Look لملفات الطباعة ثلاثية الأبعاد (نسخة تجريبية):

- **صور مصغّرة في Finder** لملفات 3MF وSTL وG-code وFreeCAD وOBJ وPLY. تُظهر ملفات 3MF وG-code وFreeCAD
  الصورة التي حفظها فيها برنامج التقطيع أو FreeCAD؛ أما ملفات STL (وملفات 3MF التي لا تحتوي على صورة)
  فتُرسَم، كما في Windows.
- **المعاينة بمفتاح المسافة:** حدّد ملفًا واضغط مفتاح المسافة. تُعرَض نماذج STL و3MF وOBJ وPLY بشكل ثلاثي
  الأبعاد (اسحب لتدويرها، ومرّر أو اقرص للتكبير) مع مقاساتها بالمليمتر. وتُظهر ملفات G-code وFreeCAD
  صورتها المحفوظة. ولكل ما عدا ذلك (الطبقات والأجسام والإعدادات) افتح الملف في PrintView3D.

يعمل ذلك بعد أن يكون PrintView3D في **Applications** وتشغّله مرة واحدة (الخطوات 1–4 أعلاه). إن لم تظهر
المعاينات، افتح **System Settings ← General ← Login Items & Extensions**، وانقر على **Quick Look**
(الرمز ⓘ بجانبه) وفعّل **PrintView3D**. يحتفظ Finder بالصور المصغّرة القديمة لبعض الوقت؛ أما الملفات التي
تنسخها أو تحفظها بعد ذلك فتظهر بالصور الجديدة. لا تُعايَن ملفات STEP: فقراءتها تحتاج إلى FreeCAD، ولا
يستطيع Quick Look استخدامه. وإن كان برنامج آخر (برنامج تقطيع أو FreeCAD) يقدّم معاينات لأحد هذه الأنواع
أيضًا، فقد يستخدم macOS معاينة ذلك البرنامج بدلًا منها.
