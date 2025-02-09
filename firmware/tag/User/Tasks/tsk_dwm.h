#ifndef __TSK_DWM
#define __TSK_DWM

#include "dwm1000.h"
#include "une_twr.h"
#include "une_tdoa.h"

class TskDWM 
{
public:
  TskDWM();
  ~TskDWM();
  void createTask();
  static void task(void const *arg);
  
private:
  DWM1000 dwm;
  UNE_TDOA une_tdoa;
  UNE_TWR une_twr;
};

#endif