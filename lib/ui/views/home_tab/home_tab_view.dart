import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:vital_step/Model/accounts.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';

import 'home_tab_viewmodel.dart';

class HomeTabView extends StackedView<HomeTabViewModel> {
  const HomeTabView({Key? key}) : super(key: key);

  @override
  Widget builder(
    BuildContext context,
    HomeTabViewModel viewModel,
    Widget? child,
  ) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text("Vital Step"),
        centerTitle: true,
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            onPressed: () {
              NavigationService()
                  .navigateToDeviceView(showExistingDevices: false);
            },
            icon: const Icon(
              Icons.devices,
            ),
          ),
        ],
      ),
      body: Container(
        padding: const EdgeInsets.all(20),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                viewModel.profile != null
                    ? "Hi, ${viewModel.profile!.name!}!"
                    : "",
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Divider(
                thickness: 2,
              ),
              viewModel.profile == null
                  ? const SizedBox(
                      height: 200,
                      child: Center(
                        child: CircularProgressIndicator(),
                      ),
                    )
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        HandProgress(
                          handName:
                              "left${viewModel.profile!.dominantHand == "Left" ? "Green" : "Red"}",
                          handProgress: viewModel.leftHandValue,
                        ),
                        HandProgress(
                          handName:
                              "right${viewModel.profile!.dominantHand == "Right" ? "Green" : "Red"}",
                          handProgress: viewModel.rightHandValue,
                        )
                      ],
                    ),
              viewModel.takeTestToGetHandAnalysis == true
                  ? Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        MaterialButton(
                          onPressed: () {
                            NavigationService().navigateToAssesmentView();
                          },
                          child: const Text("Take Test to get Hand Analysis"),
                        ),
                      ],
                    )
                  : const SizedBox(),
              const Divider(
                thickness: 2,
              ),
              verticalSpaceMedium,
              InkWell(
                onTap: () {
                  viewModel.getSpecialists();
                },
                child: const Text(
                  "Specialist having account access",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              verticalSpaceSmall,
              FutureBuilder<List<Accounts>>(
                  future: viewModel.getSpecialists(),
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    } else if (snapshot.connectionState ==
                        ConnectionState.done) {
                      if (snapshot.hasError) {
                        return const Center(child: Text("Error"));
                      } else if (snapshot.hasData) {
                        final accounts = snapshot.data;
                        if (accounts == null) {
                          return const Center(child: Text("Error"));
                        } else if (accounts.isEmpty) {
                          return const Center(child: Text("No Specialists"));
                        } else if (accounts.isNotEmpty) {
                          return SizedBox(
                              height: 66 * accounts.length.toDouble(),
                              child: ListView.builder(
                                  physics: const NeverScrollableScrollPhysics(),
                                  itemCount: accounts.length,
                                  itemBuilder:
                                      (BuildContext context, int index) {
                                    return ListTile(
                                      onTap: () {
                                        showDialog(
                                            context: context,
                                            builder: (context) {
                                              return Dialog(
                                                child: Padding(
                                                  padding: const EdgeInsets.all(
                                                      16.0),
                                                  child: Column(
                                                    crossAxisAlignment:
                                                        CrossAxisAlignment
                                                            .start,
                                                    mainAxisSize:
                                                        MainAxisSize.min,
                                                    children: [
                                                      const Row(
                                                        mainAxisAlignment:
                                                            MainAxisAlignment
                                                                .center,
                                                        children: [
                                                          Text(
                                                            'Specialist Details',
                                                            style: TextStyle(
                                                              fontSize: 20,
                                                              fontWeight:
                                                                  FontWeight
                                                                      .bold,
                                                            ),
                                                          ),
                                                        ],
                                                      ),
                                                      const SizedBox(
                                                          height: 16),
                                                      Text(
                                                          'Name: ${accounts[index].specialist?.name}'),
                                                      Text(
                                                          'Email: ${accounts[index].specialist?.email}'),
                                                      Text(
                                                          'Phone Number: ${accounts[index].specialist?.phone}'),
                                                      Text(
                                                          'Address: ${accounts[index].specialist?.city}, ${accounts[index].specialist?.country}'),
                                                      // Add more fields as necessary
                                                      const SizedBox(
                                                          height: 16),
                                                      Center(
                                                        child: MaterialButton(
                                                          color: kcPrimaryColor,
                                                          onPressed: () {
                                                            Navigator.of(
                                                                    context)
                                                                .pop();
                                                          },
                                                          child: const Text(
                                                            'Close',
                                                            style: TextStyle(
                                                                color: Colors
                                                                    .white),
                                                          ),
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                              );
                                            });
                                      },
                                      title: Text(
                                          "Specialist Id - ${accounts[index].specialist?.name}"),
                                      leading: const Icon(Icons.person),
                                    );
                                  }));
                        }
                      }
                    }
                    return SizedBox();
                  }),
              verticalSpaceMedium,
              const Text(
                "Videos",
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              verticalSpaceMedium,
              const VideoThumbNail(
                link: "https://youtu.be/pf0Tc5xrrw8Q",
                thumbNail: "thumbnail",
              ),
              verticalSpaceMedium,
            ],
          ),
        ),
      ),
    );
  }

  @override
  HomeTabViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      HomeTabViewModel();

  @override
  onViewModelReady(HomeTabViewModel viewModel) {
    viewModel.init();
  }
}

class VideoThumbNail extends StatelessWidget {
  const VideoThumbNail({
    super.key,
    required this.link,
    required this.thumbNail,
  });

  final String link;
  final String thumbNail;
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        final Uri url = Uri.parse(link);
        launchUrl(url);
      },
      child: Image.asset(
        "assets/$thumbNail.png",
        width: double.infinity,
        height: 200,
      ),
    );
  }
}

class HandProgress extends StatelessWidget {
  const HandProgress({
    super.key,
    required this.handName,
    required this.handProgress,
  });
  final String handName;
  final String handProgress;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Image.asset(
          "assets/$handName.png",
          width: 150,
          height: 150,
        ),
        verticalSpaceSmall,
        Text(
          handProgress,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
