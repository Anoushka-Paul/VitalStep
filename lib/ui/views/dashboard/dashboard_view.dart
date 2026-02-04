import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:vital_step/ui/common/ScreenHeading.dart';
import 'package:vital_step/ui/common/app_colors.dart';

import 'dashboard_viewmodel.dart';

class DashboardView extends StackedView<DashboardViewModel> {
  const DashboardView({Key? key}) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    DashboardViewModel viewModel,
    Widget? child,
  ) {
    return Container(
      color: kcPrimaryColor.withAlpha(10),
      child: Column(
        children: [
          ScreenHeading(heading: "Dashboard", showBackButton: false),
          Expanded(
            child: SingleChildScrollView(
              physics: BouncingScrollPhysics(),
              scrollDirection: Axis.vertical,
              child: Column(
                children: [
                  FAWCard("FAW"),
                  FAWCard("FBW"),
                ],
              ),
            ),
          )
        ],
      ),
    );
  }

  @override
  DashboardViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      DashboardViewModel();
}

Container FAWCard(String heading) {
  return Container(
    decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(5),
        boxShadow: [
          BoxShadow(
              offset: Offset(0, 2),
              blurRadius: 5,
              color: const Color.fromARGB(255, 222, 222, 222))
        ]),
    margin: EdgeInsets.only(left: 20, right: 20, bottom: 20),
    padding: EdgeInsets.symmetric(horizontal: 20, vertical: 20),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          child: Text(
            heading,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        SizedBox(
          height: 5,
        ),
        Divider(
          color: Color.fromARGB(255, 225, 225, 225),
        ),
        SizedBox(
          height: 10,
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            double cardWidth = (constraints.maxWidth - 40) / 3;
            return Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                CircularDataCard(
                    heading: "Current\nWeek",
                    color: Color.fromARGB(255, 146, 233, 149),
                    percentage: 50,
                    cardWidth: cardWidth),
                CircularDataCard(
                    heading: "Last\nWeek",
                    color: Color.fromARGB(255, 160, 203, 241),
                    percentage: 45,
                    cardWidth: cardWidth),
                CircularDataCard(
                    heading: "Last\nMonth",
                    color: Color.fromARGB(255, 255, 188, 199),
                    percentage: 87,
                    cardWidth: cardWidth),
              ],
            );
          },
        )
      ],
    ),
  );
}

Widget CircularDataCard(
    {required String heading,
    required double percentage,
    required double cardWidth,
    required Color color}) {
  return Container(
    width: cardWidth,
    padding: EdgeInsets.only(left: 10, right: 10, top: 15, bottom: 10),
    decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        color: Colors.white,
        boxShadow: [
          BoxShadow(
              offset: Offset(0, 2),
              blurRadius: 5,
              color: Color.fromARGB(255, 198, 198, 198))
        ]),
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          heading,
          textAlign: TextAlign.center,
          style: TextStyle(
            height: 1.2,
            fontSize: 13,
            fontWeight: FontWeight.bold,
          ),
        ),
        SizedBox(
          height: 10,
        ),
        Stack(
          children: [
            Container(
              height: cardWidth - 20,
              width: cardWidth - 20,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(200),
              ),
            ),
            Container(
              height: cardWidth - 32.5,
              width: cardWidth - 32.5,
              margin: EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(200),
              ),
              child: Center(
                child: Text(
                  "${percentage.toStringAsFixed(0)}%",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        )
      ],
    ),
  );
}
