import 'package:flutter/material.dart';
import 'package:vital_step/app/app.bottomsheets.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/ui/common/app_strings.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/ui/views/account/account_view.dart';
import 'package:vital_step/ui/views/assesment/assesment_view.dart';
import 'package:vital_step/ui/views/home_tab/home_tab_view.dart';
import 'package:vital_step/ui/views/dashboard/dashboard_view.dart';

class HomeViewModel extends BaseViewModel {
  int selectedIndex = 0;
  final List<Widget> screens = [
    const HomeTabView(),
    const DashboardView(),
    const AssesmentView(),
    const AccountView(),
  ];

  void onItemTapped(
    int index,
  ) {
    selectedIndex = index;
    rebuildUi();
  }
}
