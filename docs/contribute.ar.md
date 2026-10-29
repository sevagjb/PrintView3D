# الترجمة والمساهمة

## الترجمات {#translations}

| اللغة | الحالة |
|---|---|
| English | اللغة المصدر |
| العربية | مكتملة، راجعها متحدث أصلي |
| Nederlands | مكتملة، تمت مراجعتها |
| Deutsch | مكتملة، تحتاج إلى مراجعة متحدث أصلي |
| Français | مكتملة، تحتاج إلى مراجعة متحدث أصلي |
| Español | مكتملة، تحتاج إلى مراجعة متحدث أصلي |
| Română (الرومانية) | مكتملة، راجعها متحدث أصلي |

**تتحدث إحدى هذه اللغات؟ أو تريد PrintView3D بلغتك؟** مساعدتك مرحّب بها جدًا: حتى ملاحظة كلمة خاطئة واحدة
تساعد. تتم الترجمات هنا على GitHub مباشرةً: عدّل ملف لغتك في
[`translations/`](https://github.com/sevagjb/PrintView3D/tree/main/translations) وافتح طلب دمج (pull request)،
وكل ذلك من المتصفح. خطوة بخطوة: **[كيف تترجم](TRANSLATING.md)** (بالإنجليزية).
تظهر النصوص غير المترجمة بالإنجليزية ببساطة، لذلك يمكن إضافة لغة خطوة بخطوة.

### هذا الموقع بلغتك {#this-website-in-your-language}

كل صفحة في هذا الموقع ملف Markdown في [`docs/`](https://github.com/sevagjb/PrintView3D/tree/main/docs):
‏`install.md` بالإنجليزية، و`install.ar.md` بالعربية. لترجمة صفحة، انسخها مع رمز لغتك قبل `.md` (مثلًا
`install.nl.md`)، وترجم النص وافتح طلب دمج (تُضاف بعدها اللغة الجديدة إلى قائمة لغات الموقع). اترك الأوامر وأسماء الملفات والعلامات `{#...}` بعد العناوين كما
هي. الصفحات غير المترجمة بعد تظهر بالإنجليزية، فلا بأس بترجمة صفحة واحدة في كل مرة.

## المساهمة {#contributing}

بلاغات الأخطاء والأفكار وطلبات الدمج مرحّب بها؛ راجع [CONTRIBUTING.md](https://github.com/sevagjb/PrintView3D/blob/main/CONTRIBUTING.md).
برنامج التقطيع الخاص بك غير موجود؟ عادةً ما يكون مدخلًا واحدًا في `SLICERS` في
[`src/printview3d/slicer.py`](https://github.com/sevagjb/PrintView3D/blob/main/src/printview3d/slicer.py).

## سياسة توقيع الشيفرة {#code-signing-policy}

تُبنى إصدارات Windows تلقائيًا من هذا المستودع بواسطة
[GitHub Actions](https://github.com/sevagjb/PrintView3D/blob/main/.github/workflows/build.yml)؛ لا يُبنى أي ملف
تنفيذي ولا يُرفع يدويًا.

*الحالة: تم التقدّم بطلب توقيع مجاني للمشاريع مفتوحة المصدر. عند الموافقة:*
توقيع الشيفرة مجانًا مقدَّم من [SignPath.io](https://about.signpath.io/)، والشهادة من
[SignPath Foundation](https://signpath.org/).

| الدور | الأعضاء |
|---|---|
| المساهمون والمراجعون | [sevagjb](https://github.com/sevagjb) |
| الموافِقون | [sevagjb](https://github.com/sevagjb) |

يوافق أحد الموافِقين يدويًا على كل طلب توقيع. وتُراجَع مساهمات الآخرين قبل دمجها.

**الخصوصية:** لن ينقل هذا البرنامج أي معلومات إلى أنظمة أخرى على الشبكة إلا إذا طلب ذلك صراحةً المستخدم أو
من يثبّته أو يشغّله. يعمل PrintView3D دون اتصال بالكامل؛ فهو يفتح ملفاتك فقط ويشغّل برنامج التقطيع الذي
تختاره. الاتصال الوحيد الذي يقوم به هو التحقق من التحديثات، وفقط عندما تطلب ذلك أو تفعّل التحقق اليومي؛
راجع [التحديثات والخصوصية](use.md#updates-and-privacy).

## الترخيص {#license}

[MIT](https://github.com/sevagjb/PrintView3D/blob/main/LICENSE). مجاني للاستخدام والتعديل والمشاركة.
مبني باستخدام [Qt for Python](https://doc.qt.io/qtforpython/) و[PyVista](https://pyvista.org) و
[VTK](https://vtk.org).

## الأمان {#security}

وجدت مشكلة أمنية؟ رجاءً أبلغ عنها بشكل خاص، راجع [SECURITY.md](https://github.com/sevagjb/PrintView3D/blob/main/SECURITY.md).
